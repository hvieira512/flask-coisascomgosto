from flask_restx import Model, fields

from api.models.common import list_model

material_model = Model(
    "Material",
    {
        "id": fields.Integer(readOnly=True, description="Material ID"),
        "name": fields.String(
            required=True, description="What the piece is made of, e.g. 'Madeira'"
        ),
    },
)

material_list_model = list_model("MaterialList", "materials", material_model)

material_write_model = Model(
    "MaterialWrite",
    {
        "name": fields.String(required=True, description="Material name"),
    },
)
