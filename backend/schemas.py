# backend/schemas.py
from marshmallow import Schema, fields, validate

CATEGORY_ENUM = ("tops", "bottoms", "shoes", "accessories")

class CreateClothingItemDTO(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    category = fields.Str(required=True, validate=validate.OneOf(CATEGORY_ENUM))
    color = fields.Str(load_default=None, allow_none=True)
    image_url = fields.Str(load_default=None, allow_none=True)

class UpdateClothingItemDTO(Schema):
    name = fields.Str(validate=validate.Length(min=1))
    category = fields.Str(validate=validate.OneOf(CATEGORY_ENUM))
    color = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)

class ClothingItemDTO(Schema):
    id = fields.Int()
    name = fields.Str()
    category = fields.Str()
    color = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
