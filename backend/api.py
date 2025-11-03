from flask import Blueprint, request, abort
from flask_restx import Api, Resource, fields
from marshmallow import ValidationError
from .schemas import CreateClothingItemDTO, UpdateClothingItemDTO, ClothingItemDTO

# ---- try to use your DAO; otherwise use a tiny in-memory fallback ----
try:
    from . import dao as dao  # must expose: list_items, create_item, get_item, update_item, delete_item
except Exception:
    _items, _next_id = [], 1
    def list_items(category=None, color=None, q=None, page=1, per_page=20):
        data = _items
        if category: data = [i for i in data if i["category"] == category]
        if color: data = [i for i in data if (i.get("color") or "").lower().find(color.lower()) >= 0]
        if q: data = [i for i in data if q.lower() in i["name"].lower()]
        total = len(data); start = (page-1)*per_page; end = start+per_page
        return {"items": data[start:end], "page": page, "pages": (total+per_page-1)//per_page, "total": total}
    def create_item(name, category, color=None, image_url=None):
        global _next_id; item = {"id": _next_id, "name": name, "category": category, "color": color, "image_url": image_url}
        _items.append(item); _next_id += 1; return item
    def get_item(item_id): return next((i for i in _items if i["id"] == item_id), None)
    def update_item(item_id, **data):
        i = get_item(item_id); 
        if not i: return None
        for k,v in data.items():
            if v is not None: i[k] = v
        return i
    def delete_item(item_id):
        global _items
        before = len(_items)
        _items = [i for i in _items if i["id"] != item_id]
        return len(_items) < before
    class dao:  # shim with same API
        list_items = staticmethod(list_items)
        create_item = staticmethod(create_item)
        get_item = staticmethod(get_item)
        update_item = staticmethod(update_item)
        delete_item = staticmethod(delete_item)
# ----------------------------------------------------------------------

api_bp = Blueprint("api", __name__)
api = Api(
    api_bp,
    version="1.0",
    title="Dress Me API",
    description="Clothing items endpoints",
    doc="/docs",  # Swagger UI at /api/v1/docs
)

ns = api.namespace("items", description="Clothing items")

# models for Swagger (docs only)
ItemIn = ns.model("CreateItem", {
    "name": fields.String(required=True),
    "category": fields.String(enum=["tops","bottoms","shoes","accessories"], required=True),
    "color": fields.String,
    "image_url": fields.String,
})
ItemOut = ns.model("Item", {
    "id": fields.Integer,
    "name": fields.String,
    "category": fields.String,
    "color": fields.String,
    "image_url": fields.String,
})
ListOut = api.model("ItemListResponse", {
    "data": fields.List(fields.Nested(ItemOut)),
    "page": fields.Integer, "pages": fields.Integer, "total": fields.Integer,
})

create_schema = CreateClothingItemDTO()
update_schema = UpdateClothingItemDTO()
out_schema = ClothingItemDTO()

def dump_item(obj):  # DTO mapping (serialize)
    return out_schema.dump(obj)

@ns.route("")
class Items(Resource):
    @ns.doc(params={
        "category":"tops|bottoms|shoes|accessories",
        "color":"e.g. black",
        "q":"search by name",
        "page":"page number (default 1)",
        "per_page":"items per page (<=100, default 20)",
    })
    @ns.marshal_with(ListOut)
    def get(self):
        page = int(request.args.get("page", 1))
        per = min(int(request.args.get("per_page", 20)), 100)
        res = dao.list_items(
            category=request.args.get("category"),
            color=request.args.get("color"),
            q=request.args.get("q"),
            page=page, per_page=per
        )
        return {
            "data": [dump_item(i) for i in res["items"]],
            "page": res["page"], "pages": res["pages"], "total": res["total"]
        }

    @ns.expect(ItemIn, validate=True)
    @ns.response(201, "Created", model=ItemOut)
    def post(self):
        payload = request.get_json(force=True)
        data = create_schema.load(payload)  # validates + normalizes
        created = dao.create_item(**data)
        return dump_item(created), 201

@ns.route("/<int:item_id>")
@ns.param("item_id", "Item ID")
class ItemDetail(Resource):
    @ns.marshal_with(ItemOut)
    def get(self, item_id):
        i = dao.get_item(item_id)
        if not i: abort(404, description="Item not found")
        return dump_item(i)

    @ns.expect(ItemIn, validate=False)
    @ns.marshal_with(ItemOut)
    def put(self, item_id):
        data = update_schema.load(request.get_json(force=True) or {})
        i = dao.update_item(item_id, **data)
        if not i: abort(404, description="Item not found")
        return dump_item(i)

    @ns.response(204, "Deleted")
    def delete(self, item_id):
        ok = dao.delete_item(item_id)
        if not ok: abort(404, description="Item not found")
        return "", 204

# simple health for quick check
root = api.namespace("")
@root.route("/health")
class Health(Resource):
    def get(self): return {"status":"ok"}
