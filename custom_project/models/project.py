from odoo import _, api, fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'
    _description = 'Project Project'
    
    monto_acumulado = fields.Float(string="Monto acumulado")