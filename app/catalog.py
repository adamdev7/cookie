"""Product catalog definitions and database sync."""

from app import db
from app.models import Product

FLAVORS = [
    {
        "slug": "oreo",
        "name": "Oreo",
        "description": "Vanille, morceaux d'Oreo et chocolat blanc.",
        "price": 4.00,
        "image_url": "images/flavors/oreo.png",
    },
    {
        "slug": "red-velvet",
        "name": "Red Velvet",
        "description": "Chocolat blanc et cœur de red velvet tendre.",
        "price": 4.00,
        "image_url": "images/flavors/red-velvet.png",
    },
    {
        "slug": "lotus",
        "name": "Lotus",
        "description": "Crème de Lotus fondante et morceaux de biscuit.",
        "price": 4.00,
        "image_url": "images/flavors/lotus.png",
    },
    {
        "slug": "confetti",
        "name": "Confetti",
        "description": "Pépites de chocolat blanc et bonbons colorés.",
        "price": 4.00,
        "image_url": "images/flavors/confetti.png",
    },
    {
        "slug": "chocolat-chips",
        "name": "Chocolat chips",
        "description": "Le classique indémodable : simplement parfait !",
        "price": 4.00,
        "image_url": "images/flavors/chocolat-chips.png",
    },
    {
        "slug": "mms",
        "name": "M&M's",
        "description": "Des M&M's croquants et du chocolat au lait.",
        "price": 4.00,
        "image_url": "images/flavors/mms.png",
    },
]

BOXES = [
    {
        "slug": "box-6",
        "name": "Boîte de 6",
        "description": "Composez votre boîte de 6 biscuits au choix.",
        "box_size": 6,
    },
    {
        "slug": "box-12",
        "name": "Boîte de 12",
        "description": "Composez votre boîte de 12 biscuits au choix.",
        "box_size": 12,
    },
]


def sync_catalog(unit_price: float = 4.0) -> None:
    """Create or update flavors and box products."""
    box_6_price = round(unit_price * 6, 2)
    box_12_price = round(unit_price * 12, 2)

    for data in FLAVORS:
        data = {**data, "price": unit_price}
        product = Product.query.filter_by(slug=data["slug"]).first()
        if not product:
            product = Product(slug=data["slug"], product_kind=Product.KIND_FLAVOR)
            db.session.add(product)
        product.name = data["name"]
        product.description = data["description"]
        product.price = data["price"]
        product.image_url = data["image_url"]
        product.is_active = True
        product.product_kind = Product.KIND_FLAVOR
        product.box_size = None

    box_prices = {6: box_6_price, 12: box_12_price}
    for data in BOXES:
        product = Product.query.filter_by(slug=data["slug"]).first()
        if not product:
            product = Product(slug=data["slug"], product_kind=Product.KIND_BOX)
            db.session.add(product)
        product.name = data["name"]
        product.description = data["description"]
        product.price = box_prices[data["box_size"]]
        product.image_url = "images/hero-cookies-box.png"
        product.is_active = True
        product.product_kind = Product.KIND_BOX
        product.box_size = data["box_size"]

    valid_slugs = {d["slug"] for d in FLAVORS} | {d["slug"] for d in BOXES}
    Product.query.filter(
        Product.slug.is_(None) | (~Product.slug.in_(valid_slugs))
    ).update({Product.is_active: False}, synchronize_session=False)

    db.session.commit()


def get_active_flavors():
    return (
        Product.query.filter_by(is_active=True, product_kind=Product.KIND_FLAVOR)
        .order_by(Product.id)
        .all()
    )


def get_box_product(size: int):
    return Product.query.filter_by(
        is_active=True, product_kind=Product.KIND_BOX, box_size=size
    ).first()
