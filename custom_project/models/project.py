from odoo import _, api, fields, models
from odoo.exceptions import UserError

# It is specified that the account will be of type Expenses ID
ACCOUNT_ACCOUNT_TYPE_ID = 15


class ProjectProject(models.Model):
    _inherit = 'project.project'
    _description = 'Project Project'
    
    monto_acumulado = fields.Monetary(string="Monto acumulado", currency_field="currency_id")
    show_btn_to_close = fields.Boolean(compute='compute_close_project', default=False)
    show_btn_reopen = fields.Boolean(compute='compute_reopen_project', default=False)
    show_account = fields.Boolean(compute='compute_show_account', default=False)
    state_project = fields.Selection(selection=[("open", "Abierto"), ("close", "Cerrado")], default="open")
    account_account = fields.Many2one(comodel_name='account.account', string='Cuenta Contable',
                                      domain="[('user_type_id', '=', " + str(ACCOUNT_ACCOUNT_TYPE_ID) + ")]")
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Activo fijo', readonly=True)

    def write(self, vals):
        for project_id in self:
            if project_id.state_project == 'close' and not \
                    ('state_project' in vals and self.user_has_groups('project.group_project_manager')) and\
                    not ('product_tmpl_id' in vals):
                raise UserError(_("No se puede modificar un proyecto cerrado."))
        res = super(ProjectProject, self).write(vals)
        return res

    def compute_reopen_project(self):
        for project_id in self:
            project_id.show_btn_reopen = True if (
                    project_id.state_project == 'close' and self.user_has_groups('project.group_project_manager')
            ) else False

    def compute_show_account(self):
        for project_id in self:
            if project_id.date:
                project_id.show_account = True if project_id.date >= fields.Date.today() else False
            else:
                project_id.show_account = False

    def compute_close_project(self):
        for project_id in self:
            if project_id.date:
                project_id.show_btn_to_close = True if (
                        project_id.date >= fields.Date.today() and project_id.state_project == 'open'
                ) else False
            else:
                project_id.show_btn_to_close = False

    def reopen_project(self):
        for project_id in self:
            project_id.sudo().state_project = 'open'

    def close_project(self):
        for project_id in self:
            if not project_id.account_account:
                raise UserError(_("No se puede cerrar el proyecto sin una cuenta de gastos definida."))
            project_id.state_project = 'close'

    def button_fixed_asset(self):
        if self.product_tmpl_id:
            raise UserError(_("No se puede volver a crear el activo fijo una vez creado."))
        product_category_id = self.env['product.category'].search([('is_asset', '=', True)], limit=1)
        product_tmpl_id = self.env['product.template'].create({
            "name": self.name,
            "standard_price": self.monto_acumulado,
            "is_asset": True,
            "categ_id": product_category_id.id,
        })
        self.product_tmpl_id = product_tmpl_id
