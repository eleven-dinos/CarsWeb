from app.models import VEHICLE_STATUSES, Client, Vehicle, Yard

DIGITS = "0123456789"
CODE_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"


def clean(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def only_has(text, allowed):
    for character in text:
        if character not in allowed:
            return False
    return True


def length_ok(text, min_length, max_length):
    if len(text) < min_length:
        return False
    if len(text) > max_length:
        return False
    return True


def is_valid_email(email):
    if not length_ok(email, 3, 254):
        return False
    for character in email:
        if character.isspace():
            return False
    if email.count("@") != 1:
        return False
    parts = email.split("@")
    name = parts[0]
    domain = parts[1]
    if name == "":
        return False
    if "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    return True


def is_valid_code(code, max_length):
    if not length_ok(code, 1, max_length):
        return False
    return only_has(code, CODE_CHARACTERS)


def is_valid_id(text):
    if not length_ok(text, 1, 9):
        return False
    return only_has(text, DIGITS)


def price_to_cents(text):
    if text.count(".") > 1:
        return None

    if "." in text:
        parts = text.split(".")
        whole = parts[0]
        decimals = parts[1]
        if not length_ok(decimals, 1, 2):
            return None
    else:
        whole = text
        decimals = ""

    if not length_ok(whole, 1, 9):
        return None
    if not only_has(whole, DIGITS):
        return None
    if not only_has(decimals, DIGITS):
        return None

    while len(decimals) < 2:
        decimals = decimals + "0"

    return int(whole) * 100 + int(decimals)


def validate_yard(form, db, yard_id=None):
    data = {}
    data["name"] = clean(form.get("name"))
    data["location"] = clean(form.get("location"))

    errors = {}
    if not length_ok(data["name"], 1, 100):
        errors["name"] = "Name must be between 1 and 100 characters."
    if not length_ok(data["location"], 1, 200):
        errors["location"] = "Location must be between 1 and 200 characters."

    if "name" not in errors:
        existing = db.query(Yard).filter(Yard.name == data["name"]).first()
        if existing is not None and existing.id != yard_id:
            errors["name"] = "A yard with this name already exists."

    return data, errors


def validate_client(form):
    data = {}
    data["name"] = clean(form.get("name"))
    data["email"] = clean(form.get("email"))
    data["country"] = clean(form.get("country"))

    errors = {}
    if not length_ok(data["name"], 1, 100):
        errors["name"] = "Name must be between 1 and 100 characters."
    if not is_valid_email(data["email"]):
        errors["email"] = "Enter a valid email address."
    if not length_ok(data["country"], 1, 100):
        errors["country"] = "Country must be between 1 and 100 characters."

    return data, errors


def validate_vehicle(form, db, vehicle_id=None):
    data = {}
    data["stock_number"] = clean(form.get("stock_number")).upper()
    data["chassis_number"] = clean(form.get("chassis_number")).upper()
    data["make"] = clean(form.get("make"))
    data["model"] = clean(form.get("model"))
    data["year"] = clean(form.get("year"))
    data["price"] = clean(form.get("price"))
    data["status"] = clean(form.get("status"))
    data["client_id"] = clean(form.get("client_id"))
    data["yard_id"] = clean(form.get("yard_id"))

    errors = {}

    if not is_valid_code(data["stock_number"], 20):
        errors["stock_number"] = "Stock number must be 1 to 20 letters, numbers or hyphens."

    if not is_valid_code(data["chassis_number"], 30):
        errors["chassis_number"] = "Chassis number must be 1 to 30 letters, numbers or hyphens."

    if not length_ok(data["make"], 1, 100):
        errors["make"] = "Make must be between 1 and 100 characters."

    if not length_ok(data["model"], 1, 100):
        errors["model"] = "Model must be between 1 and 100 characters."

    if not length_ok(data["year"], 1, 4) or not only_has(data["year"], DIGITS) or int(data["year"]) < 1:
        errors["year"] = "Year must be a whole number greater than 0."

    cents = price_to_cents(data["price"])
    if cents is None or cents <= 0:
        errors["price"] = "Price must be a positive amount in euro, for example 12500.00."

    if data["status"] not in VEHICLE_STATUSES:
        errors["status"] = "Choose a valid status."

    if data["client_id"] != "":
        if not is_valid_id(data["client_id"]):
            errors["client_id"] = "Choose a valid client."
        elif db.get(Client, int(data["client_id"])) is None:
            errors["client_id"] = "Choose a valid client."

    if not is_valid_id(data["yard_id"]):
        errors["yard_id"] = "Choose a valid yard."
    elif db.get(Yard, int(data["yard_id"])) is None:
        errors["yard_id"] = "Choose a valid yard."

    if "stock_number" not in errors:
        existing = db.query(Vehicle).filter(Vehicle.stock_number == data["stock_number"]).first()
        if existing is not None and existing.id != vehicle_id:
            errors["stock_number"] = "This stock number is already in use."

    if "chassis_number" not in errors:
        existing = db.query(Vehicle).filter(Vehicle.chassis_number == data["chassis_number"]).first()
        if existing is not None and existing.id != vehicle_id:
            errors["chassis_number"] = "This chassis number is already in use."

    return data, errors
