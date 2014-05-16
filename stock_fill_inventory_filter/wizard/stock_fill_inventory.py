# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import _

class stock_fill_inventory(osv.TransientModel):
    _inherit = 'stock.fill.inventory'
    _columns = {
        'category_ids': fields.many2many('product.category',
                                         string=u'Filter by category'),
    }

    def fill_inventory(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}

        inventory_line_obj = self.pool.get('stock.inventory.line')
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        if ids and len(ids):
            ids = ids[0]
        else:
             return {'type': 'ir.actions.act_window_close'}
        fill_inventory = self.browse(cr, uid, ids, context=context)
        res = {}
        res_location = {}

        if fill_inventory.recursive:
            location_ids = location_obj.search(cr, uid, [('location_id',
                             'child_of', [fill_inventory.location_id.id])], order="id",
                             context=context)
        else:
            location_ids = [fill_inventory.location_id.id]

        res = {}
        flag = False
        category_condition = False
        if fill_inventory.category_ids:
            category_condition = [('product_id.categ_id.id', 'in',
                             [c.id for c in fill_inventory.category_ids])]
        for location in location_ids:
            datas = {}
            res[location] = {}
            search_condition = ['|', ('location_dest_id', '=', location),
                                ('location_id', '=', location),
                                ('state', '=', 'done')]
            if category_condition:
                search_condition.extend(category_condition)
            move_ids = move_obj.search(cr, uid, search_condition, context=context)

            for move in move_obj.browse(cr, uid, move_ids, context=context):
                lot_id = move.prodlot_id.id
                prod_id = move.product_id.id
                if move.location_dest_id.id != move.location_id.id:
                    if move.location_dest_id.id == location:
                        qty = uom_obj._compute_qty(cr, uid, move.product_uom.id,move.product_qty, move.product_id.uom_id.id)
                    else:
                        qty = -uom_obj._compute_qty(cr, uid, move.product_uom.id,move.product_qty, move.product_id.uom_id.id)


                    if datas.get((prod_id, lot_id)):
                        qty += datas[(prod_id, lot_id)]['product_qty']

                    datas[(prod_id, lot_id)] = {'product_id': prod_id, 'location_id': location, 'product_qty': qty, 'product_uom': move.product_id.uom_id.id, 'prod_lot_id': lot_id}

            if datas:
                flag = True
                res[location] = datas

        if not flag:
            raise osv.except_osv(_('Warning!'), _('No product in this location. Please select a location in the product form.'))

        for stock_move in res.values():
            for stock_move_details in stock_move.values():
                stock_move_details.update({'inventory_id': context['active_ids'][0]})
                domain = []
                for field, value in stock_move_details.items():
                    if field == 'product_qty' and fill_inventory.set_stock_zero:
                         domain.append((field, 'in', [value,'0']))
                         continue
                    domain.append((field, '=', value))

                if fill_inventory.set_stock_zero:
                    stock_move_details.update({'product_qty': 0})

                line_ids = inventory_line_obj.search(cr, uid, domain, context=context)

                if not line_ids:
                    inventory_line_obj.create(cr, uid, stock_move_details, context=context)

        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
