"""Development seed, built from the workshop's own Facebook page.

Sources, August 2026:
  facebook.com/coisascomgosto.vianadocastelo — page description, cover montage,
  photo grid and the "7º dia" / "9º dia" reels from the Agonia fair.

The collections are the three motif families the page names itself:
"Artefactos em madeira decorados com motivos de inspiração na Filigrana, nos
Bordados e nos Lenços."

Re-runnable: it clears the catalog tables first. Users are left alone.

    flask --app app seed
"""

from api.db import get_db_connection
from api.repositories import (
    CategoryRepository,
    CollectionRepository,
    ColorRepository,
    ColorSetRepository,
    ContactRepository,
    EventRepository,
    ProductRepository,
    ProductImageRepository,
    ProductTypeRepository,
    SizeRepository,
    ProductVariantRepository,
)

CATALOG_TABLES = [
    "product_images",
    "product_sizes",
    "product_variants",
    "products",
    "color_set_colors",
    "color_sets",
    "colors",
    "product_types",
    "collections",
    "categories",
    "events",
]

COLORS = [
    ("Branco", "#F5F3EF"),
    ("Preto", "#1B1A18"),
    ("Dourado", "#C9A227"),
    ("Vermelho", "#B3282D"),
    ("Azul", "#2C5FA8"),
    ("Azul-marinho", "#1F2A44"),
    ("Verde", "#2E6B4F"),
]

# Motif families, straight from the page description.
COLLECTIONS = [
    ("Filigrana", "Os volutas e corações da filigrana de Viana, desenhados a "
                  "pincel sobre a madeira."),
    ("Bordados", "Os motivos dos bordados de Viana, passados para peças de "
                 "madeira e bastidores."),
    ("Lenços", "As flores e as cores dos Lenços dos Namorados."),
]

# (collection, set name, colours in order)
COLOR_SETS = [
    ("Filigrana", "Branco e Dourado", ["Branco", "Dourado"]),
    ("Filigrana", "Preto e Dourado", ["Preto", "Dourado"]),
    ("Filigrana", "Preto e Branco", ["Preto", "Branco"]),
    ("Filigrana", "Vermelho e Branco", ["Vermelho", "Branco"]),
    ("Filigrana", "Azul e Branco", ["Azul", "Branco"]),
    ("Bordados", "Branco e Azul", ["Branco", "Azul"]),
    ("Bordados", "Verde e Dourado", ["Verde", "Dourado"]),
    ("Lenços", "Preto Floral", ["Preto", "Vermelho", "Verde"]),
    ("Lenços", "Vermelho Floral", ["Vermelho", "Branco", "Verde"]),
]

# (name, icon, description, [sub-types]) — sub-types nest exactly one level.
PRODUCT_TYPES = [
    ("Caixa", "fa-box",
     "Caixas de madeira pintadas à mão, de guardar joias, missangas ou "
     "recordações.",
     [("Caixa redonda", "fa-circle-dot", "Tampa redonda, muitas vezes com "
                                         "boneco no topo."),
      ("Caixa rectangular", "fa-box", "A forma clássica, em vários tamanhos."),
      ("Caixa alta", "fa-box-archive", "Mais funda, para garrafas ou canetas.")]),

    ("Coração", "fa-heart",
     "O coração de Viana recortado em madeira.",
     [("Coração de pendurar", "fa-heart", "Com fita, para pendurar à parede."),
      ("Coração com base", "fa-heart", "De pé, como peça de mesa.")]),

    ("Moldura", "fa-image",
     "Molduras de fotografia com janela recta ou oval.", []),

    ("Bastidor", "fa-circle-notch",
     "O bastidor de bordar, pintado ou com letras à mão.", []),

    ("Enfeite de Natal", "fa-gift",
     "Enfeites de árvore, personalizados com o nome.",
     [("Coração de Natal", "fa-heart", "Coração pequeno com fita."),
      ("Bola de Natal", "fa-circle", "Bola achatada em madeira.")]),

    ("Abre-cápsulas", "fa-wine-bottle",
     "Abre-cápsulas de madeira com pega decorada.", []),
]

# (name, sub-type, collection, description, colour sets, sizes)
# collection is the product's own; None exercises the nullable column.
PRODUCTS = [
    ("Caixa Redonda Filigrana", "Caixa redonda", "Filigrana",
     "Caixa redonda com a filigrana desenhada a pincel na tampa.",
     ["Branco e Dourado", "Preto e Dourado", "Preto e Branco",
      "Vermelho e Branco", "Azul e Branco"],
     ["S", "M", "L"]),

    ("Caixa Redonda Manel e Maria", "Caixa redonda", "Filigrana",
     "Caixa redonda com o par do Minho em traje sobre a tampa.",
     ["Vermelho e Branco", "Preto e Branco"], ["M"]),

    ("Caixa de Joias", "Caixa rectangular", "Filigrana",
     "Caixa rectangular forrada, para joias e missangas.",
     ["Branco e Dourado", "Preto e Dourado", "Vermelho e Branco"],
     ["S", "M", "L"]),

    ("Caixa Lenço dos Namorados", "Caixa rectangular", "Lenços",
     "Tampa com as flores do Lenço dos Namorados.",
     ["Preto Floral", "Vermelho Floral"], ["M"]),

    ("Caixa de Garrafa", "Caixa alta", "Filigrana",
     "Caixa alta para uma garrafa, decorada nas quatro faces.",
     ["Preto e Dourado", "Azul e Branco"], []),

    ("Coração de Viana", "Coração de pendurar", "Filigrana",
     "Coração recortado em madeira, com fita para pendurar.",
     ["Branco e Dourado", "Preto e Dourado", "Azul e Branco",
      "Vermelho e Branco"], ["S", "M"]),

    ("Coração de Mesa", "Coração com base", "Filigrana",
     "Coração assente numa base, para ficar de pé.",
     ["Branco e Dourado", "Preto e Branco"], ["M"]),

    ("Moldura Filigrana", "Moldura", "Filigrana",
     "Moldura de fotografia com filigrana à volta da janela.",
     ["Branco e Dourado", "Preto e Dourado", "Vermelho e Branco"],
     ["S", "M", "L"]),

    ("Moldura Oval", "Moldura", "Filigrana",
     "Janela oval, com o motivo a subir pelos lados.",
     ["Branco e Dourado", "Preto e Dourado"], ["M"]),

    ("Bastidor Viana é Amor", "Bastidor", "Bordados",
     "Bastidor com letras desenhadas à mão e a filigrana à volta.",
     ["Branco e Dourado", "Branco e Azul"], ["M"]),

    ("Bastidor Bordado", "Bastidor", "Bordados",
     "Bastidor com os motivos dos bordados de Viana.",
     ["Branco e Azul", "Verde e Dourado"], ["S", "M"]),

    ("Coração de Natal", "Coração de Natal", None,
     "Enfeite de árvore em coração, personalizado com o nome.",
     ["Vermelho e Branco", "Branco e Dourado"], ["S"]),

    ("Bola de Natal", "Bola de Natal", None,
     "Enfeite de árvore em bola achatada, personalizado com o nome.",
     ["Vermelho e Branco", "Branco e Dourado"], ["S"]),

    ("Abre-cápsulas Coração", "Abre-cápsulas", "Filigrana",
     "Abre-cápsulas com pega em coração.",
     ["Preto e Dourado", "Preto e Branco"], []),
]


# Photographs lifted from the page's own albums, cropped square.
# (product, colour set or None for a product-wide fallback, file, alt)
IMAGES = [
    ("Caixa Redonda Filigrana", None, "caixa-redonda-dourado.jpg",
     "Caixa redonda branca com coração de filigrana a dourado"),
    ("Caixa Redonda Filigrana", "Azul e Branco", "caixa-redonda-azul.jpg",
     "Três caixas redondas brancas com filigrana azul"),
    ("Caixa Redonda Filigrana", "Preto e Branco", "caixa-preto-branco.jpg",
     "Caixa redonda preta com filigrana branca"),
    ("Caixa Redonda Filigrana", "Vermelho e Branco", "caixa-coracao-vermelho.jpg",
     "Caixa vermelha em forma de coração com filigrana dourada"),

    ("Caixa Redonda Manel e Maria", None, "manel-e-maria.jpg",
     "O par do Minho em traje sobre um coração dourado"),

    ("Caixa de Joias", None, "caixa-preto-dourado.jpg",
     "Peças pretas com filigrana dourada"),

    ("Moldura Oval", None, "moldura-rosa.jpg",
     "Moldura branca de janela oval com filigrana rosa"),

    ("Bastidor Bordado", None, "bastidor-nome.jpg",
     "Bastidor bordado à mão com um nome ao centro"),

    ("Coração de Natal", None, "coracao-natal-nome.jpg",
     "Coração de Viana branco com nome escrito a dourado"),

    ("Abre-cápsulas Coração", None, "abre-capsulas.jpg",
     "Três abre-cápsulas de madeira com motivos pintados"),
    ("Caixa Lenço dos Namorados", None, "caixa-lenco-rosas.jpg",
     "Caixa branca com as rosas do Lenço dos Namorados na tampa"),

    ("Coração de Viana", None, "coracao-branco-nome.jpg",
     "Coração de Viana branco com nome escrito a dourado"),
    ("Coração de Viana", "Vermelho e Branco", "coracao-vermelho-nome.jpg",
     "Coração de Viana vermelho com letras douradas"),

    ("Coração de Mesa", None, "coracao-mesa-figura.jpg",
     "Coração de pé com uma figura em traje minhoto"),
    ("Coração de Mesa", "Branco e Dourado", "coracao-mesa-par.jpg",
     "Coração de pé com o par do Minho e a frase quem ama fica"),

    ("Moldura Filigrana", None, "moldura-branco.jpg",
     "Moldura branca com filigrana prateada"),
    ("Moldura Filigrana", "Preto e Dourado", "moldura-preto-dourado.jpg",
     "Moldura preta com janela oval e filigrana dourada"),

    ("Bastidor Viana é Amor", None, "bastidor-dourado.jpg",
     "Bastidor com um coração de Viana bordado a dourado"),
    ("Bastidor Viana é Amor", "Branco e Azul", "bastidor-azul-nome.jpg",
     "Bastidor com coração bordado a azul e um nome"),

    ("Bola de Natal", None, "bola-natal-branco.jpg",
     "Bastidor branco com coração dourado e laço vermelho"),
    ("Bola de Natal", "Vermelho e Branco", "bola-natal-vermelho.jpg",
     "Três bastidores vermelhos com filigrana branca"),
    ("Bola de Natal", None, "bola-natal-azul.jpg",
     "Bastidor azul-escuro com coração dourado, pendurado na árvore"),

    ("Coração de Natal", "Vermelho e Branco", "coracao-natal-branco.jpg",
     "Coração de Viana branco com nome, na árvore"),
]

EVENTS = [
    ("XXIV Exposição/Feira de Artesanato da Romaria d'Agonia",
     "Jardim Público, Viana do Castelo",
     "Cerca de 50 expositores, dezassete dias de feira no jardim.",
     "2026-08-07", "2026-08-23",
     "https://www.facebook.com/coisascomgosto.vianadocastelo/"),
]

CONTACT = {
    "address": "Rua de Cardielos, n. 222, Viana do Castelo",
    "email": "geral@coisascomgosto.pt",
    "whatsapp": "939320334",
    "maps_url": "https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9",
    "facebook_url": "https://www.facebook.com/coisascomgosto.vianadocastelo/",
    "instagram_url": "https://www.instagram.com/coisascomgosto.vianadocastelo/",
}


def seed():
    with get_db_connection() as (_, cursor):
        for table in CATALOG_TABLES:
            cursor.execute(f"TRUNCATE TABLE `{table}`")

        categories = CategoryRepository(cursor)
        collections = CollectionRepository(cursor)
        colors = ColorRepository(cursor)
        color_sets = ColorSetRepository(cursor)
        types = ProductTypeRepository(cursor)
        products = ProductRepository(cursor)
        variants = ProductVariantRepository(cursor)
        sizes = SizeRepository(cursor)
        events = EventRepository(cursor)

        category_id = categories.create("Madeira")

        color_ids = {name: colors.create(name=name, hex=hex_) for name, hex_ in COLORS}

        collection_ids = {
            name: collections.create(name=name, description=description)
            for name, description in COLLECTIONS
        }

        set_ids = {}
        for collection, name, colour_names in COLOR_SETS:
            set_ids[name] = color_sets.create(
                name=name,
                collection_id=collection_ids[collection],
                color_ids=[color_ids[c] for c in colour_names],
            )

        type_ids = {}
        for name, icon, description, sub_types in PRODUCT_TYPES:
            parent_id = types.create(name=name, icon=icon, description=description)
            type_ids[name] = parent_id
            for sub_name, sub_icon, sub_description in sub_types:
                type_ids[sub_name] = types.create(
                    name=sub_name,
                    parent_id=parent_id,
                    icon=sub_icon,
                    description=sub_description,
                )

        size_ids = {s["name"]: s["id"] for s in sizes.list(limit=50, offset=0)}

        product_ids = {}
        variant_ids = {}
        for name, type_name, collection, description, set_names, size_names in PRODUCTS:
            product_id = products.create(
                name=name,
                category_id=category_id,
                type_id=type_ids[type_name],
                collection_id=collection_ids[collection] if collection else None,
                description=description,
            )
            product_ids[name] = product_id
            for set_name in set_names:
                variant_ids[(name, set_name)] = variants.create(
                    product_id=product_id, color_set_id=set_ids[set_name]
                )
            if size_names:
                products.set_sizes(
                    product_id, [size_ids[s] for s in size_names if s in size_ids]
                )

        images = ProductImageRepository(cursor)
        position = {}
        for product_name, set_name, filename, alt in IMAGES:
            key = product_name
            position[key] = position.get(key, 0) + 1
            images.create(
                product_id=product_ids[product_name],
                variant_id=variant_ids.get((product_name, set_name)),
                url=f"/static/img/products/{filename}",
                alt=alt,
                position=position[key],
            )

        for name, location, description, starts_on, ends_on, url in EVENTS:
            events.create(
                name=name,
                location=location,
                description=description,
                starts_on=starts_on,
                ends_on=ends_on,
                url=url,
            )

        ContactRepository(cursor).update(**CONTACT)

    print(
        f"Seeded {len(PRODUCTS)} products, "
        f"{sum(1 + len(t[3]) for t in PRODUCT_TYPES)} product types, "
        f"{len(COLOR_SETS)} colour sets, {len(IMAGES)} images, {len(EVENTS)} event."
    )
