import sys
import os
import json
import tempfile
import shutil
from fastapi.testclient import TestClient

# Asegura que el directorio raíz esté en sys.path (por si se ejecuta desde test/)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app  # importa la app FastAPI
import src.base as val

client = TestClient(app)

def setup_module(module):
    # Crear directorio temporal para el archivo data.json de test
    module.tmpdir = tempfile.mkdtemp()
    persistent_dir = os.path.join(module.tmpdir, "persistent")
    os.makedirs(persistent_dir, exist_ok=True)

    # Crear archivo JSON vacío para almacenar pagos de test
    module.datafile = os.path.join(persistent_dir, "data.json")
    with open(module.datafile, "w") as f:
        json.dump({}, f)

    # Redirigir la ruta de datos de la app hacia el archivo temporal
    val.DATA_PATH = module.datafile
    print(f" Tests usando archivo temporal: {module.datafile}")

def teardown_module(module):
    # Eliminar directorio temporal después de correr los tests
    shutil.rmtree(module.tmpdir)


# T01
def test_create_and_pay_paypal():
    """Flujo normal: crear un pago PayPal válido y pagarlo."""
    r = client.post("/payments/1", params={"amount": 2000, "payment_method": "paypal"})
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "REGISTRADO"

    rpay = client.post("/payments/1/pay")
    assert rpay.status_code == 200
    assert rpay.json()["data"]["status"] == "PAGADO"


# T02
def test_paypal_fail_and_revert():
    """Pago PayPal con monto > 5000 debe fallar y poder revertirse."""
    r = client.post("/payments/2", params={"amount": 6000, "payment_method": "paypal"})
    assert r.status_code == 201

    rpay = client.post("/payments/2/pay")
    assert rpay.status_code == 200
    assert rpay.json()["data"]["status"] == "FALLIDO"

    rrev = client.post("/payments/2/revert")
    assert rrev.status_code == 200
    assert rrev.json()["data"]["status"] == "REGISTRADO"


# T03
def test_credit_card_validation():
    """No se permiten dos pagos REGISTRADOS con tarjeta de crédito."""
    r1 = client.post("/payments/3", params={"amount": 200, "payment_method": "tarjeta"})
    assert r1.status_code == 201
    assert r1.json()["data"]["status"] == "REGISTRADO"

    # Segundo pago con tarjeta
    r2 = client.post("/payments/4", params={"amount": 300, "payment_method": "tarjeta"})
    assert r2.status_code == 201

    # Intentar pagar el segundo -> debe FALLAR porque ya hay uno REGISTRADO
    rpay2 = client.post("/payments/4/pay")
    assert rpay2.status_code == 200
    data = val.load_payment("4")
    assert data["status"] == "FALLIDO"


# T04
def test_register_duplicate_returns_409():
    """Registrar un id existente debe fallar (409)."""
    # Crear
    r1 = client.post("/payments/200", params={"amount": 100, "payment_method": "PayPal"})
    assert r1.status_code == 201

    # Re-crear mismo id => conflicto
    r2 = client.post("/payments/200", params={"amount": 100, "payment_method": "PayPal"})
    assert r2.status_code == 409
    assert "ya existe" in r2.json()["detail"].lower()


# T05
def test_pay_nonexistent_returns_404():
    """Pagar un id inexistente debe devolver 404."""
    r = client.post("/payments/999999/pay")
    assert r.status_code == 404
    assert "no existe" in r.json()["detail"].lower()


# T06
def test_register_invalid_amount_returns_422():
    """Registrar con amount inválido debe devolver 422."""
    # amount <= 0 viola Query(gt=0.0)
    r = client.post("/payments/201", params={"amount": 0, "payment_method": "PayPal"})
    assert r.status_code == 422


# T07
def test_register_empty_method_returns_422():
    """Registrar con payment_method vacío debe devolver 422."""
    # payment_method vacío viola Query(min_length=1)
    r = client.post("/payments/202", params={"amount": 100, "payment_method": ""})
    assert r.status_code == 422


# T08
def test_pay_unknown_method_returns_409_and_keeps_registered():
    """Pagar con método no soportado debe fallar (409) sin cambiar estado."""
    # Registrar con método no soportado (se valida recién al pagar)
    r1 = client.post("/payments/203", params={"amount": 100, "payment_method": "Bitcoin"})
    assert r1.status_code == 201

    # Al pagar, get_validator() debería fallar => endpoint devuelve 409
    r2 = client.post("/payments/203/pay")
    assert r2.status_code == 409
    assert "no soportado" in r2.json()["detail"].lower()

    # El estado no debería cambiar, porque no llegó a persistir transición
    all_payments = client.get("/payments").json()["all_payments"]
    assert all_payments["203"]["status"] == "REGISTRADO"


# T09
def test_update_after_paid_returns_409():
    """Actualizar un pago PAGADO debe fallar (409)."""
    client.post("/payments/204", params={"amount": 100, "payment_method": "PayPal"})

    rp = client.post("/payments/204/pay")
    assert rp.status_code == 200
    assert rp.json()["data"]["status"] == "PAGADO"

    # Update en PAGADO debe fallar por State => endpoint 409
    ru = client.post("/payments/204/update", params={"amount": 200, "payment_method": "PayPal"})
    assert ru.status_code == 409
    assert "no se puede actualizar" in ru.json()["detail"].lower()


# T10
def test_revert_registered_returns_409():
    """Revertir un pago REGISTRADO debe fallar (409)."""
    client.post("/payments/205", params={"amount": 100, "payment_method": "PayPal"})

    # Revert en REGISTRADO debe fallar => endpoint 409
    rr = client.post("/payments/205/revert")
    assert rr.status_code == 409
    assert "no se puede revertir" in rr.json()["detail"].lower()


# T11
def test_pay_twice_returns_409_on_second_attempt():
    """Pagar dos veces el mismo id debe fallar en el segundo intento (409)."""
    client.post("/payments/206", params={"amount": 100, "payment_method": "PayPal"})

    r1 = client.post("/payments/206/pay")
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "PAGADO"

    # Pagar de nuevo en PAGADO => State lanza => endpoint 409
    r2 = client.post("/payments/206/pay")
    assert r2.status_code == 409
    assert "ya está pagado" in r2.json()["detail"].lower()


# T12
def test_revert_nonexistent_returns_404():
    """Revertir un pago inexistente debe devolver 404."""
    r = client.post("/payments/999998/revert")
    assert r.status_code == 404
    assert "no existe" in r.json()["detail"].lower()


# T13
def test_update_nonexistent_returns_404():
    """Actualizar un pago inexistente debe devolver 404."""
    r = client.post(
        "/payments/999997/update",
        params={"amount": 100, "payment_method": "paypal"},
    )
    assert r.status_code == 404
    assert "no existe" in r.json()["detail"].lower()


# T14
def test_update_registered_success():
    """Actualizar un pago REGISTRADO debe cambiar amount y payment_method."""
    r = client.post("/payments/208", params={"amount": 2000, "payment_method": "paypal"})
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "REGISTRADO"

    rupd = client.post("/payments/208/update", params={"amount": 2500, "payment_method": "paypal"})
    assert rupd.status_code == 200
    assert rupd.json()["data"]["status"] == "REGISTRADO"

    # Verificar persistencia (datos efectivamente actualizados)
    data = val.load_payment("208")
    assert data["amount"] == 2500
    assert data["payment_method"] == "paypal"
    assert data["status"] == "REGISTRADO"
