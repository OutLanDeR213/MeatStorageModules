# meat_storage_cost

Модуль для Odoo 18, який вирішує просту задачу: м'ясна компанія тримає товар у холодильнику і платить за зберігання щодня. Модуль автоматично накручує цю вартість на собівартість кожної партії.

## Як це працює

Щодня планувальник проходить по всіх залишках на складі з методом FIFO і додає до кожного шару `stock.valuation.layer` додаткову вартість зберігання:

```
вартість = кількість (кг) × 0.01 USD
```

Якщо товар в штуках - береться `product.weight`. Якщо в кг - конвертується через UoM.

Собівартість не чіпається напряму в `product.product` - це заборонено умовою задачі. Замість цього створюється новий запис у `stock.valuation.layer` з `quantity=0` і `value=вартість_зберігання`. Це стандартний Odoo-підхід, яким користуються Landed Costs.

## Звіти

**Storage Cost Log** - журнал кожного нарахування: коли, який продукт, скільки кг, яка сума.

**Storage Cost Report** - зведена таблиця по партіях: початкова собівартість, скільки разів нараховували, поточна собівартість. Є pivot і tree view.

Меню: `Inventory → Operations → Storage Costs`

## Встановлення

1. Скопіювати папку `meat_storage_cost` в папку з кастомними модулями
2. Додати шлях до `addons_path` в `odoo.conf`
3. Перезапустити сервер
4. Встановити модуль через Apps або командою:

```bash
C:\odootest\venv\Scripts\python.exe C:\odootest\odoo-18.0.post20251213\setup\odoo -c C:\odootest\odoo.conf -d odootest -u meat_storage_cost
```

## REST API

Модуль надає три ендпоінти для зовнішніх інтеграцій.

### Аутентифікація

Всі запити потребують API ключ в заголовку:
```
Authorization: Bearer <api_key>
```

**Де взяти ключ:** Settings → Users & Companies → Users → обери юзера → вкладка **API Keys** → **New API Key**.

### Ендпоінти

```
GET  /api/v1/storage-costs              — список нарахувань (пагінація)
GET  /api/v1/storage-costs?product_id=5 — фільтр по продукту
GET  /api/v1/storage-costs/report       — зведений звіт по партіях
POST /api/v1/storage-costs/run          — запустити нарахування вручну
```

### Приклад запиту

```bash
curl -X GET http://localhost:8069/api/v1/storage-costs \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Формат відповіді

```json
{
  "success": true,
  "total": 42,
  "limit": 50,
  "offset": 0,
  "data": [
    {
      "id": 1,
      "date": "2026-04-26",
      "product": "Beef Test",
      "lot": null,
      "quantity_kg": 500.0,
      "storage_cost": 5.0,
      "initial_unit_cost": 200.0,
      "adjustment_number": 1
    }
  ]
}
```

## Вимоги

- Odoo 18 Community
- Залежності: `stock`, `stock_account`
- Категорія продукту повинна мати метод оцінки **FIFO**
