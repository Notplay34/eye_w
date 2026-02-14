# Прейскурант центра: документ → цена (₽).
# Шаблон number.docx — изготовление номера, добавляется отдельно при need_plate.

from decimal import Decimal
from typing import Optional

PRICE_LIST = [
    {"template": "mreo.docx", "label": "МРЭО (постановка/снятие)", "price": Decimal("500")},
    {"template": "DKP.docx", "label": "ДКП", "price": Decimal("500")},
    {"template": "dkp_dar.docx", "label": "ДКП дарение", "price": Decimal("500")},
    {"template": "dkp_pieces.docx", "label": "ДКП запчасти", "price": Decimal("500")},
    {"template": "doverennost.docx", "label": "Доверенность", "price": Decimal("300")},
    {"template": "zaiavlenie.docx", "label": "Заявление", "price": Decimal("200")},
    {"template": "akt_pp.docx", "label": "Акт приёма-передачи", "price": Decimal("300")},
    {"template": "prokuratura.docx", "label": "Прокуратура", "price": Decimal("400")},
    {"template": "number.docx", "label": "Изготовление номера", "price": Decimal("1500")},
]

def get_price_by_template(template: str) -> Optional[Decimal]:
    for item in PRICE_LIST:
        if item["template"] == template:
            return item["price"]
    return None

def get_label_by_template(template: str) -> str:
    for item in PRICE_LIST:
        if item["template"] == template:
            return item["label"]
    return template
