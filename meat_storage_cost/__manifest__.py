{
    'name': 'Meat Storage Daily Cost',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Daily storage cost accrual for FIFO cold warehouse',
    'depends': ['stock', 'stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/stock_storage_cost_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
