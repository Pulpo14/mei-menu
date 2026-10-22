
import streamlit as st
import gspread
import html
from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================

st.set_page_config(
    page_title="Mei Menu",
    page_icon="🍜",
    layout="wide"
)

# ==========================================
# CARGAR DISEÑO
# ==========================================

ruta_css = Path(__file__).parent / "styles.css"

try:
    with open(ruta_css, "r", encoding="utf-8") as archivo:
        st.markdown(
            f"<style>{archivo.read()}</style>",
            unsafe_allow_html=True
        )
except FileNotFoundError:
    st.warning("No se encontró styles.css junto a app.py.")

# ==========================================
# FUNCIONES
# ==========================================

def formato_pesos(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


def convertir_precio(valor):
    texto = str(valor or "").strip()

    if not texto or texto.lower() == "consultar":
        return None

    texto = texto.replace("$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")

    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def agregar_producto(nombre, precio):
    if nombre not in st.session_state.carrito:
        st.session_state.carrito[nombre] = {
            "precio": precio,
            "cantidad": 0
        }

    st.session_state.carrito[nombre]["cantidad"] += 1


def cambiar_cantidad(nombre, cambio):
    if nombre not in st.session_state.carrito:
        return

    st.session_state.carrito[nombre]["cantidad"] += cambio

    if st.session_state.carrito[nombre]["cantidad"] <= 0:
        del st.session_state.carrito[nombre]


# ==========================================
# INICIAR CARRITO
# ==========================================

if "carrito" not in st.session_state:
    st.session_state.carrito = {}

# ==========================================
# ENCABEZADO
# ==========================================

st.markdown("""
<div class="hero">
    <div class="hero-tag">COCINA CHINA</div>
    <div class="hero-title">🍜 Mei Menu</div>
    <div class="hero-subtitle">
        Tus platos favoritos, a un solo toque.
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE SHEETS Y MENÚ
# ==========================================

try:
    # Conexión segura compatible con Streamlit Cloud
    if "gcp_service_account" in st.secrets:
        gc = gspread.service_account_from_dict(
            dict(st.secrets["gcp_service_account"])
        )
    else:
        # Conexión local en tu computador
        gc = gspread.service_account(
            filename=str(
                Path(__file__).parent
                / "mei-menu-b8318fccec3c.json"
            )
        )

    spreadsheet = gc.open_by_key(
        "1jQhvExi6Myu9pbltDVhR9QJNL3GvY-53Q6GQLiUFUaw"
    )

    hoja = spreadsheet.worksheet("Menu")
    datos = hoja.get_all_records()

    productos_disponibles = [
        p for p in datos
        if str(p.get("Disponible", "SI")).strip().upper() == "SI"
        and str(p.get("Producto", "")).strip()
    ]

    if not productos_disponibles:
        st.warning("Todavía no hay productos disponibles.")

    else:
        # ==========================================
        # BUSCADOR Y CATEGORÍAS
        # ==========================================

        st.subheader("🔎 Encuentra tu plato")
        st.caption("Busca por nombre o explora las categorías.")

        col_busqueda, col_categoria = st.columns([2, 1])

        with col_busqueda:
            busqueda = st.text_input(
                "Buscar producto",
                placeholder="Ej: pollo, arroz, wantán...",
                key="buscador_productos"
            )

        todas_categorias = sorted({
            str(p.get("Categoria") or "Otros").strip() or "Otros"
            for p in productos_disponibles
        })

        with col_categoria:
            filtro_categoria = st.selectbox(
                "Categoría",
                ["Todas las categorías"] + todas_categorias,
                key="filtro_categoria"
            )

        productos_filtrados = []

        for producto in productos_disponibles:
            nombre = str(producto.get("Producto", "")).strip()
            categoria = (
                str(producto.get("Categoria") or "Otros").strip()
                or "Otros"
            )

            coincide_nombre = (
                busqueda.strip().lower() in nombre.lower()
            )

            coincide_categoria = (
                filtro_categoria == "Todas las categorías"
                or categoria == filtro_categoria
            )

            if coincide_nombre and coincide_categoria:
                productos_filtrados.append(producto)

        st.divider()

        if not productos_filtrados:
            st.info("No encontramos productos con esos filtros.")

        else:
            productos_por_categoria = {}

            for producto in productos_filtrados:
                categoria = (
                    str(producto.get("Categoria") or "Otros").strip()
                    or "Otros"
                )

                productos_por_categoria.setdefault(
                    categoria, []
                ).append(producto)

            st.subheader("Explora nuestro menú")

            for categoria, productos_categoria in productos_por_categoria.items():
                st.header(categoria)
                columnas = st.columns(2)

                for i, producto in enumerate(productos_categoria):
                    nombre = str(producto.get("Producto", "")).strip()
                    descripcion = str(
                        producto.get("Descripcion") or ""
                    ).strip()

                    precio = convertir_precio(
                        producto.get("Precio")
                    )

                    if precio is None:
                        texto_precio = (
                            "Consultar precio"
                            if str(producto.get("Precio") or "")
                            .strip().lower() == "consultar"
                            else "Precio no disponible"
                        )
                    else:
                        texto_precio = formato_pesos(precio)

                    with columnas[i % 2]:
                        with st.container(border=True):
                            st.subheader(nombre)

                            if descripcion:
                                st.write(descripcion)

                            st.markdown(
                                '<div class="price">'
                                + html.escape(texto_precio)
                                + '</div>',
                                unsafe_allow_html=True
                            )

                            if precio is not None:
                                if st.button(
                                    "＋ Agregar al pedido",
                                    key=f"agregar_{categoria}_{i}_{nombre}",
                                    use_container_width=True
                                ):
                                    agregar_producto(nombre, precio)
                                    st.rerun()
                            else:
                                st.caption(
                                    "Precio pendiente de confirmar."
                                )

                st.divider()

    # ==========================================
    # CARRITO FLOTANTE CLICKEABLE
    # ==========================================

    cantidad_total = sum(
        item["cantidad"]
        for item in st.session_state.carrito.values()
    )

    monto_total = sum(
        item["precio"] * item["cantidad"]
        for item in st.session_state.carrito.values()
    )

    if cantidad_total > 0:
        st.markdown(
            f"""
            <a href="#carrito" class="carrito-flotante">
                🛒 Mi pedido · {cantidad_total} ·
                {formato_pesos(monto_total)}
            </a>
            """,
            unsafe_allow_html=True
        )

    # ==========================================
    # DESTINO DEL ENLACE Y CARRITO COMPLETO
    # ==========================================

    st.markdown(
        '<div id="carrito"></div>',
        unsafe_allow_html=True
    )

    st.header("🛒 Tu pedido")

    if not st.session_state.carrito:
        st.info("Todavía no has agregado productos.")

        st.markdown("""
        <div class="cart-total">
            <div class="cart-label">Total del pedido</div>
            <div class="cart-amount">$0</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        for nombre, item in list(st.session_state.carrito.items()):
            cantidad = item["cantidad"]
            precio = item["precio"]
            subtotal = cantidad * precio

            st.markdown(f"**{html.escape(nombre)}**")

            (
                col_precio,
                col_menos,
                col_cantidad,
                col_mas,
                col_subtotal
            ) = st.columns([2, 1, 1, 1, 2])

            with col_precio:
                st.write(formato_pesos(precio))

            with col_menos:
                if st.button(
                    "−",
                    key=f"menos_{nombre}",
                    use_container_width=True
                ):
                    cambiar_cantidad(nombre, -1)
                    st.rerun()

            with col_cantidad:
                st.markdown(
                    f"<div style='text-align:center; padding-top:8px;'>"
                    f"<strong>{cantidad}</strong></div>",
                    unsafe_allow_html=True
                )

            with col_mas:
                if st.button(
                    "＋",
                    key=f"mas_{nombre}",
                    use_container_width=True
                ):
                    cambiar_cantidad(nombre, 1)
                    st.rerun()

            with col_subtotal:
                st.write(f"**{formato_pesos(subtotal)}**")

            st.divider()

        total = sum(
            item["precio"] * item["cantidad"]
            for item in st.session_state.carrito.values()
        )

        st.markdown(f"""
        <div class="cart-total">
            <div class="cart-label">Total del pedido</div>
            <div class="cart-amount">{formato_pesos(total)}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Vaciar pedido", use_container_width=True):
            st.session_state.carrito = {}
            st.rerun()

except Exception as e:
    st.error(
        "No se pudo conectar con Google Sheets o cargar el menú."
    )
    st.caption(
        "Revisa la conexión, las credenciales y los nombres de las columnas."
    )
    st.code(str(e))
