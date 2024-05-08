from odoo import _, api, fields, models
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

# It is specified that the account will be of type Expenses ID
ACCOUNT_ACCOUNT_TYPE_ID = 15


class ProjectProject(models.Model):
    _inherit = 'project.project'
    _description = 'Project Project'
    
    monto_acumulado = fields.Monetary(string="Monto acumulado", currency_field="currency_id")
    show_btn_to_close = fields.Boolean(compute='compute_close_project')
    show_btn_reopen = fields.Boolean(compute='compute_reopen_project')
    show_account = fields.Boolean(compute='compute_show_account')
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
        if vals.get('analytic_account_id') != self.analytic_account_id.id and self.analytic_account_id.line_ids.filtered(lambda x: x.project_id.id == self.id):
            raise UserError(_("No se puede modificar la cuenta analítica de un proyecto que ya tiene lineas analiticas.\n Elimine la linea analítica del proyecto primero."))
        res = super(ProjectProject, self).write(vals)
        self._create_account_analytic_line(vals)
        return res
    
    @api.model
    def create(self, vals):
        res = super(ProjectProject, self).create(vals)
        res._create_account_analytic_line(vals)
        return res
    
    def _create_account_analytic_line(self, vals):
        analytic_account = vals.get('analytic_account_id', self.analytic_account_id.id)
        monto_acumulado = vals.get('monto_acumulado', self.monto_acumulado)
        analytic_account_id = self.env['account.analytic.account'].browse(analytic_account) if analytic_account else False
        line_ids = analytic_account_id.line_ids if analytic_account_id else []
        if monto_acumulado and analytic_account:
            if  len(line_ids) == 0:
                self.env['account.analytic.line'].create({
                    'name': self.name,
                    'account_id': analytic_account_id.id,
                    'date': fields.Date.today(),
                    'amount': monto_acumulado,
                    'company_id': self.company_id.id,
                    'project_id': self.id,
                })
            elif len(line_ids) == 1 and line_ids[0].name == self.name and line_ids[0].account_id.id == analytic_account_id.id:
                line_ids[0].amount = monto_acumulado

    def cron_create_account_analytic_line(self):
        records = self.browse([])
        for record in records:
            try:
                record._create_account_analytic_line({})
            except Exception as error:
                _logger.error(f'Error al crear línea de cuenta analítica: {error}\n del projecto {record.name}')
            else:
                continue

    def compute_reopen_project(self):
        for project_id in self:
            project_id.show_btn_reopen = True if (
                    project_id.state_project == 'close' and self.user_has_groups('project.group_project_manager')
            ) else False

    def compute_show_account(self):
        for project_id in self:
            if project_id.date:
                project_id.show_account = True if project_id.date <= fields.Date.today() else False
            else:
                project_id.show_account = False

    def compute_close_project(self):
        for project_id in self:
            if project_id.date:
                project_id.show_btn_to_close = True if (
                        project_id.date <= fields.Date.today() and project_id.state_project == 'open'
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
