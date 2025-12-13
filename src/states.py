
""" Patrón State """

from src.base import STATUS_FALLIDO, STATUS_PAGADO, STATUS_REGISTRADO
from src.validators import (
    get_validator
)

class PaymentState:
    def pay(self, context): raise NotImplementedError
    def update(self, context, amount, method): raise NotImplementedError
    def revert(self, context): raise NotImplementedError

class RegisteredState(PaymentState):
    def pay(self, context):
        validator = get_validator(context.payment_method)
        valid = validator.validate(context.payment_id, context.amount, context.payment_method)
        if valid:
            context.status = STATUS_PAGADO
            context.set_state(PaidState())
        else:
            context.status = STATUS_FALLIDO
            context.set_state(FailedState())
        context._persist()

    def update(self, context, amount, method):
        context.amount = amount
        context.payment_method = method
        context._persist()

    def revert(self, context):
        raise Exception("No se puede revertir un pago REGISTRADO")

class PaidState(PaymentState):
    def pay(self, context): raise Exception("El pago ya está PAGADO")
    def update(self, context, amount, method): raise Exception("No se puede actualizar un pago PAGADO")
    def revert(self, context): raise Exception("No se puede revertir un pago PAGADO")

class FailedState(PaymentState):
    def pay(self, context): raise Exception("No se puede pagar un pago FALLIDO. Revertir a REGISTRADO antes")

    def update(self, context, amount, method):
        raise Exception("No se puede actualizar un pago FALLIDO")

    def revert(self, context):
        context.status = STATUS_REGISTRADO
        context.set_state(RegisteredState())
        context._persist()
