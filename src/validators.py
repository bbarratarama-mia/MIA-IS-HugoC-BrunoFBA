""" Validadores de métodos de pago """

from src.base import load_all_payments
from src.base import STATUS, PAYMENT_METHOD, STATUS_REGISTRADO

class PaymentValidator:
    def validate(self, payment_id, amount, payment_method):
        raise NotImplementedError

class CreditCardValidator(PaymentValidator):
    def validate(self, payment_id, amount, payment_method):
        if amount >= 10000:
            return False
        # no más de un pago REGISTRADO con tarjeta
        payments = load_all_payments()
        registrados = [p for p in payments.values()
                       if p[PAYMENT_METHOD] == payment_method and p[STATUS] == STATUS_REGISTRADO]
        return len(registrados) <= 1

class PayPalValidator(PaymentValidator):
    def validate(self, payment_id, amount, payment_method):
        return amount < 5000

def get_validator(payment_method: str):
    method = payment_method.lower()
    if "tarjeta" in method or "card" in method:
        return CreditCardValidator()
    elif "paypal" in method:
        return PayPalValidator()
    raise Exception(f"Método de pago no soportado: {payment_method}")
