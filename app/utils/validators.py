from marshmallow import Schema, fields, validate, validates, ValidationError as MarshmallowError


class LoginSchema(Schema):
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=50),
        error_messages={"required": "Username wajib diisi."},
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Password wajib diisi."},
    )


class ChangePasswordSchema(Schema):
    old_password = fields.Str(
        required=True,
        error_messages={"required": "Password lama wajib diisi."},
    )
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error="Password baru minimal 8 karakter."),
        error_messages={"required": "Password baru wajib diisi."},
    )


# ← Tidak ada indent di sini, sejajar dengan class di atas
class SensorReadingSchema(Schema):
    water_level_cm = fields.Float(required=True)
    temperature_c  = fields.Float(load_default=None, allow_none=True)
    humidity_pct   = fields.Float(load_default=None, allow_none=True)
    sensor_status  = fields.Str(
        load_default="ONLINE",
        validate=validate.OneOf(["ONLINE", "DELAY", "OFFLINE"])
    )
    recorded_at    = fields.DateTime(load_default=None, allow_none=True)

    @validates("water_level_cm")
    def validate_water_level(self, value):
        if value < 0 or value > 500:
            raise MarshmallowError("water_level_cm harus antara 0–500 cm")


login_schema = LoginSchema()
change_password_schema = ChangePasswordSchema()