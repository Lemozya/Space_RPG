from math import atan2, cos, degrees, sin
from pathlib import Path
import ctypes
import builtins
import json
import time as py_time
from ursina import *
from direct.task import Task
from panda3d.core import LineSegs, TransparencyAttrib, WindowProperties
from ursina.mesh_importer import load_model
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.sky import Sky
from ursina.texture_importer import load_texture
import random


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = PROJECT_ROOT / "assets"
EXTERNAL_ASSETS_ROOT = ASSETS_ROOT / "external"
GENERATED_ASSETS_ROOT = ASSETS_ROOT / "generated"
KENNEY_ROOT = EXTERNAL_ASSETS_ROOT / "Starter-Kit-FPS"
KENNEY_MODELS = KENNEY_ROOT / "models"
KENNEY_SPRITES = KENNEY_ROOT / "sprites"
KENNEY_UI_ROOT = EXTERNAL_ASSETS_ROOT / "kenney_ui_pack"
KENNEY_UI_BLUE_DOUBLE = KENNEY_UI_ROOT / "PNG" / "Blue" / "Default"
KENNEY_UI_YELLOW_DOUBLE = KENNEY_UI_ROOT / "PNG" / "Yellow" / "Default"
AI_ASS_ROOT = EXTERNAL_ASSETS_ROOT / "AI_ass"
URSINA_REPO_TEXTURES = EXTERNAL_ASSETS_ROOT / "ursina_repo" / "ursina" / "textures"
KHRONOS_MODELS_ROOT = EXTERNAL_ASSETS_ROOT / "Khronos_Sample_Assets" / "Models"
KHRONOS_CESIUMMAN = KHRONOS_MODELS_ROOT / "CesiumMan" / "glTF-Binary"
KHRONOS_RIGGEDSIMPLE = KHRONOS_MODELS_ROOT / "RiggedSimple" / "glTF-Binary"
POLY_PIZZA_ROOT = EXTERNAL_ASSETS_ROOT / "poly_pizza"
STAR_MAP_SPEC_PATH = PROJECT_ROOT / "Star.json"

BODY_FONT = "segoeui.ttf"
TITLE_FONT = "segoeuib.ttf"
TECH_FONT = "consola.ttf"

ROOM_HALF_SIZE = 12
ROOM_HEIGHT = 6
MAP_MESSAGE_DURATION = 0.55
MAP_OPEN_DELAY = 0.35

map_message_timer = 0.0
map_open_queued = False
saber_is_swinging = False
world_motion_time = 0.0
WINDOW_MODE_ORDER = ("windowed", "borderless", "fullscreen")
WINDOW_MODE_LABELS = {
    "windowed": "\u0412 \u0440\u0430\u043c\u043a\u0435",
    "borderless": "\u0411\u0435\u0437 \u0440\u0430\u043c\u043a\u0438",
    "fullscreen": "\u041f\u043e\u043b\u043d\u044b\u0439 \u044d\u043a\u0440\u0430\u043d",
}
WINDOWED_SCALE_PRESETS = (0.72, 0.82, 0.90, 0.96)
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
UI_REFERENCE_SIZE = (1920, 1080)
UI_BASE_SCALE = 0.86
UI_MIN_SCALE = 0.64
UI_MAX_SCALE = 0.92
ui_scale_factor = 1.0
ui_roots = []
ui_layout_subscribers = []
UI_DESIGN_BOUNDS = {
    "left": -0.86,
    "right": 0.86,
    "top": 0.46,
    "bottom": -0.46,
}
UI_SAFE_MARGIN_PX = {
    "x": 64,
    "y": 44,
}
UI_TEXT_ROLE_BASE_SCALE = {
    "title": 0.98,
    "subtitle": 0.56,
    "body": 0.54,
    "meta": 0.46,
    "hint": 0.44,
    "hud_title": 0.72,
}
UI_TEXT_ROLE_CLAMP = {
    "title": (0.74, 1.12),
    "subtitle": (0.44, 0.70),
    "body": (0.38, 0.66),
    "meta": (0.32, 0.56),
    "hint": (0.30, 0.52),
    "hud_title": (0.52, 0.86),
}
UI_BUTTON_TEXT_BASE = 0.030
UI_BUTTON_TEXT_MIN = 0.022
UI_BUTTON_TEXT_MAX = 0.036


class UIScaleManager:
    def __init__(self, reference_size):
        self.reference_width = max(1, int(reference_size[0]))
        self.reference_height = max(1, int(reference_size[1]))
        self.reference_aspect = self.reference_width / self.reference_height
        self.width = self.reference_width
        self.height = self.reference_height
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.uniform_scale = UI_BASE_SCALE
        self.aspect = self.reference_aspect
        self.narrow_factor = 0.0
        self.wide_factor = 0.0
        self.safe_left = UI_DESIGN_BOUNDS["left"]
        self.safe_right = UI_DESIGN_BOUNDS["right"]
        self.safe_top = UI_DESIGN_BOUNDS["top"]
        self.safe_bottom = UI_DESIGN_BOUNDS["bottom"]

    def update(self, width, height):
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.scale_x = self.width / self.reference_width
        self.scale_y = self.height / self.reference_height
        self.aspect = self.width / self.height
        self.narrow_factor = clamp((self.reference_aspect / max(0.001, self.aspect)) - 1.0, 0.0, 1.0)
        self.wide_factor = clamp((self.aspect / self.reference_aspect) - 1.0, 0.0, 1.0)

        raw_uniform = min(self.scale_x, self.scale_y)
        self.uniform_scale = clamp(raw_uniform * UI_BASE_SCALE, UI_MIN_SCALE, UI_MAX_SCALE)

        margin_x = (UI_SAFE_MARGIN_PX["x"] / self.reference_width) * (1.0 + self.narrow_factor * 0.45)
        margin_y = (UI_SAFE_MARGIN_PX["y"] / self.reference_height)
        self.safe_left = UI_DESIGN_BOUNDS["left"] + margin_x
        self.safe_right = UI_DESIGN_BOUNDS["right"] - margin_x
        self.safe_top = UI_DESIGN_BOUNDS["top"] - margin_y
        self.safe_bottom = UI_DESIGN_BOUNDS["bottom"] + margin_y

    def safe_rect(self):
        return self.safe_left, self.safe_right, self.safe_top, self.safe_bottom

    def anchor(self, horizontal="center", vertical="center", offset=(0.0, 0.0)):
        x_lookup = {
            "left": self.safe_left,
            "center": (self.safe_left + self.safe_right) * 0.5,
            "right": self.safe_right,
        }
        y_lookup = {
            "top": self.safe_top,
            "center": (self.safe_top + self.safe_bottom) * 0.5,
            "bottom": self.safe_bottom,
        }
        x_value = x_lookup.get(horizontal, x_lookup["center"]) + offset[0]
        y_value = y_lookup.get(vertical, y_lookup["center"]) + offset[1]
        return x_value, y_value

    def panel_width(self, base_width, min_width, max_width):
        adjusted = base_width * (1.0 + self.narrow_factor * 0.30 - self.wide_factor * 0.10)
        return clamp(adjusted, min_width, max_width)

    def text_scale(self, role, multiplier=1.0):
        base_scale = UI_TEXT_ROLE_BASE_SCALE.get(role, UI_TEXT_ROLE_BASE_SCALE["body"])
        min_scale, max_scale = UI_TEXT_ROLE_CLAMP.get(role, UI_TEXT_ROLE_CLAMP["body"])
        aspect_adjust = 1.0 - self.narrow_factor * 0.08
        target = base_scale * multiplier * aspect_adjust
        return clamp(target, min_scale, max_scale)

    def button_text_size(self, legacy_value):
        legacy_multiplier = clamp(float(legacy_value) / 0.36, 0.72, 1.35)
        target = UI_BUTTON_TEXT_BASE * legacy_multiplier * (1.0 - self.narrow_factor * 0.05)
        return clamp(target, UI_BUTTON_TEXT_MIN, UI_BUTTON_TEXT_MAX)


ui_scale_manager = UIScaleManager(UI_REFERENCE_SIZE)


def C(r, g, b, a=255):
    return color.rgba32(r, g, b, a)


def detect_display_monitors():
    fallback = [{"name": "\u041c\u043e\u043d\u0438\u0442\u043e\u0440 1", "x": 0, "y": 0, "width": 1280, "height": 720, "primary": True}]
    try:
        user32 = ctypes.windll.user32
        try:
            # Prefer per-monitor v2 DPI awareness so monitor/window coordinates are
            # consistent on scaled desktop setups (125%, 150%, etc.).
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
                ("szDevice", ctypes.c_wchar * 32),
            ]

        monitors = []

        def _callback(handle, _dc, _rect, _data):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                rect = info.rcMonitor
                monitors.append(
                    {
                        "name": info.szDevice or f"Monitor {len(monitors) + 1}",
                        "x": rect.left,
                        "y": rect.top,
                        "width": rect.right - rect.left,
                        "height": rect.bottom - rect.top,
                        "primary": bool(info.dwFlags & 1),
                    }
                )
            return 1

        monitor_enum_proc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_long,
        )
        user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(_callback), 0)
        monitors.sort(key=lambda item: (0 if item["primary"] else 1, item["x"], item["y"]))
        for index, monitor in enumerate(monitors):
            monitor["label"] = f"\u041c\u043e\u043d\u0438\u0442\u043e\u0440 {index + 1} ({monitor['width']}x{monitor['height']})"
        return monitors or fallback
    except Exception:
        return fallback


DISPLAY_MONITORS = detect_display_monitors()
display_settings = {
    "monitor_index": 0,
    "window_mode": "windowed",
    "window_scale_index": 2,
}
mouse_capture_request_id = 0
mouse_focus_restore_timer = 0.0
window_event_suppressed_until = 0.0


def register_ui_layout(callback):
    if callback and callback not in ui_layout_subscribers:
        ui_layout_subscribers.append(callback)


def refresh_ui_layouts():
    for callback in tuple(ui_layout_subscribers):
        try:
            callback()
        except Exception as error:
            callback_name = getattr(callback, "__name__", repr(callback))
            print(f"[Space RPG] UI layout callback failed ({callback_name}): {error}")


def apply_text_role(text_entity, role, multiplier=1.0, color_value=None, font_value=None, line_height=None):
    if not text_entity:
        return
    text_entity.scale = ui_scale_manager.text_scale(role, multiplier=multiplier)
    if color_value is not None:
        text_entity.color = color_value
    if font_value is not None:
        text_entity.font = font_value
    if line_height is not None:
        text_entity.line_height = line_height


def load_json_data(path):
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"[Space RPG] JSON load failed for {path.name}: {error}")
        return {}


STAR_MAP_SPEC = load_json_data(STAR_MAP_SPEC_PATH)


THREAT_LABELS = {
    "Low": "Низкий",
    "Moderate": "Средний",
    "High": "Высокий",
    "Critical": "Критический",
    "Severe": "Тяжёлый",
}


GALAXY_SYSTEMS = [
    {
        "name": "Станция Валькир",
        "position": (-0.52, -0.08),
        "size": 0.040,
        "tint": C(106, 164, 255),
        "region": "Внутренние рубежи",
        "threat": "Low",
        "summary": "Точка базирования флота, доки и дипломатический трафик. Сейчас именно здесь пришвартован твой корабль.",
    },
    {
        "name": "Врата Сигнуса",
        "position": (-0.22, 0.16),
        "size": 0.034,
        "tint": C(96, 236, 255),
        "region": "Релейный коридор",
        "threat": "Moderate",
        "summary": "Древняя релейная архитектура, вокруг которой выросли современные таможенные узлы и патрульные маршруты.",
    },
    {
        "name": "Корона Эоса",
        "position": (-0.04, -0.20),
        "size": 0.028,
        "tint": C(255, 195, 120),
        "region": "Бассейн Гелиоса",
        "threat": "Low",
        "summary": "Промышленная система с верфями, топливными кольцами и хорошо охраняемыми гражданскими трассами.",
    },
    {
        "name": "Завеса Персея",
        "position": (0.18, 0.24),
        "size": 0.032,
        "tint": C(150, 134, 255),
        "region": "Призрачный простор",
        "threat": "High",
        "summary": "Ионные штормы и фантомные сигнатуры сенсоров делают этот сектор удобным для контрабанды и скрытых заходов.",
    },
    {
        "name": "Пояс Хепри",
        "position": (0.30, -0.04),
        "size": 0.026,
        "tint": C(255, 150, 110),
        "region": "Пепельная граница",
        "threat": "High",
        "summary": "Добывающие колонии держатся за обломки лун, пока на трассах спорят за контроль частные военные флоты.",
    },
    {
        "name": "Бастион Никс",
        "position": (0.48, 0.08),
        "size": 0.036,
        "tint": C(255, 98, 122),
        "region": "Внешний оборонный пояс",
        "threat": "Critical",
        "summary": "Милитаризованная мёртвая зона. Здесь крепки не только оборонительные сетки, но и политические интересы.",
    },
    {
        "name": "Разлом Орфея",
        "position": (0.02, 0.42),
        "size": 0.029,
        "tint": C(118, 255, 210),
        "region": "Поющая туманность",
        "threat": "Moderate",
        "summary": "Светящееся аномальное поле, которое разведчики используют, чтобы скрывать тихие заходы в сектор.",
    },
    {
        "name": "Дредмайр",
        "position": (-0.34, -0.34),
        "size": 0.024,
        "tint": C(180, 120, 255),
        "region": "Чёрный дрейф",
        "threat": "Severe",
        "summary": "Кладбище дрейфующих обломков, заполненное кланами сборщиков, разрушенными носителями и нестабильными маяками.",
    },
]

GALAXY_ROUTES = [
    ("Станция Валькир", "Врата Сигнуса"),
    ("Станция Валькир", "Дредмайр"),
    ("Врата Сигнуса", "Корона Эоса"),
    ("Врата Сигнуса", "Завеса Персея"),
    ("Врата Сигнуса", "Разлом Орфея"),
    ("Корона Эоса", "Пояс Хепри"),
    ("Завеса Персея", "Бастион Никс"),
    ("Пояс Хепри", "Бастион Никс"),
    ("Дредмайр", "Корона Эоса"),
]
GALAXY_SYSTEM_LOOKUP = {entry["name"]: entry for entry in GALAXY_SYSTEMS}


class ShipTechnicianMind:
    def __init__(self):
        self.session_count = 0
        self.topic_counts = {
            "greet": 0,
            "status": 0,
            "route": 0,
            "identity": 0,
            "datapad": 0,
            "bye": 0,
        }
        self.last_system_name = None

    def open_dialogue(self, current_system_name):
        self.session_count += 1
        current_system = GALAXY_SYSTEM_LOOKUP[current_system_name]

        if self.session_count == 1:
            opening_line = "Привет. Я как раз свожу диагностику по борту. Что тебе подсветить?"
        elif self.last_system_name != current_system_name:
            opening_line = f"Уже на векторе {current_system_name}. Я обновил сводку по этому сектору."
        elif current_system["threat"] in ("High", "Critical", "Severe"):
            opening_line = "Я держу техконтур под наблюдением. В этом секторе расслабляться рано."
        else:
            opening_line = "Снова на связи. Корабль тихий, но я всё равно слежу за показаниями."

        self.last_system_name = current_system_name
        return opening_line, self._build_choices(current_system_name)

    def _build_choices(self, current_system_name):
        current_system = GALAXY_SYSTEM_LOOKUP[current_system_name]
        route_label = "Есть риски по курсу?" if current_system["threat"] in ("High", "Critical", "Severe") else "Что по маршруту?"
        if self.topic_counts["route"] and current_system["threat"] in ("Low", "Moderate"):
            route_label = "Куда лететь спокойнее?"

        topic_id = "identity" if self.topic_counts["identity"] == 0 else "datapad"
        topic_label = "Кто ты?" if topic_id == "identity" else "Что на датападе?"

        return [
            {"id": "greet", "label": "Снова привет." if self.topic_counts["greet"] else "Привет."},
            {"id": "status", "label": "Повтори статус корабля." if self.topic_counts["status"] else "Что с кораблём?"},
            {"id": "route", "label": route_label},
            {"id": topic_id, "label": topic_label},
            {"id": "bye", "label": "Пока."},
        ]

    def respond(self, choice_id, current_system_name):
        current_system = GALAXY_SYSTEM_LOOKUP[current_system_name]
        self.topic_counts[choice_id] = self.topic_counts.get(choice_id, 0) + 1

        if choice_id == "greet":
            if self.topic_counts["greet"] == 1:
                reply = "Привет. На корпусе тихо, реактор в зелёной зоне, сюрпризов не вижу."
            else:
                reply = "Снова привет. Я всё ещё над калибровкой, но в целом борт ведёт себя спокойно."
            return reply, self._build_choices(current_system_name), False

        if choice_id == "status":
            if self.topic_counts["status"] > 1:
                reply = "С прошлого доклада почти ничего не изменилось: магистрали ровные, щиты без просадок, тепло держу в допуске."
            elif current_system["threat"] in ("Critical", "Severe"):
                reply = f"Реактор стабилен, но я держу запас по охлаждению. {current_system['name']} любит перегружать сенсоры и экраны."
            elif current_system["threat"] == "High":
                reply = f"Силовые контуры в норме, но сектор {current_system['name']} шумный. Я уже подкрутил фильтры и тепловой резерв."
            elif current_system["threat"] == "Moderate":
                reply = f"Щиты и привод ровные. Для района {current_system['region']} это хороший, спокойный набор показаний."
            else:
                reply = "Все основные контуры зелёные: двигатель, жизнеобеспечение и обшивка без красных флагов."
            return reply, self._build_choices(current_system_name), False

        if choice_id == "route":
            if current_system["threat"] in ("Critical", "Severe"):
                reply = f"Если идём к {current_system['name']}, не дави двигатель в пик. Там лучше иметь тихий ход и запас по температуре."
            elif current_system["threat"] == "High":
                reply = f"На {current_system['name']} я бы держал сенсоры в активном фильтре. Сектор нервный, зато корабль к нему уже подготовлен."
            elif current_system["threat"] == "Moderate":
                reply = f"Маршрут на {current_system['name']} рабочий. Просто не забывай про топливо и не режь трассу через шумные карманы."
            else:
                reply = f"Курс на {current_system['name']} чистый. Можно идти спокойно, без лишнего стресса для систем."
            return reply, self._build_choices(current_system_name), False

        if choice_id == "identity":
            reply = "Я бортовой техник. Держу в строю силовые линии, крепления корпуса и всю ту мелочь, о которой вспоминают только когда она ломается."
            return reply, self._build_choices(current_system_name), False

        if choice_id == "datapad":
            if self.topic_counts["datapad"] == 1:
                reply = f"На датападе журналы отказов, температура катушек и пометки по сектору {current_system['name']}. Пока всё жёлтое, красного нет."
            else:
                reply = "Те же журналы, только свежее. Я обновляю их быстрее, чем мостик успевает задавать новые вопросы."
            return reply, self._build_choices(current_system_name), False

        if choice_id == "bye":
            reply = "Принял. Если что-то заискрит или маршрут станет грязнее, я буду здесь, с датападом под рукой."
            return reply, self._build_choices(current_system_name), True

        return "Канал чист. Спрашивай, если понадобится ещё что-то по борту.", self._build_choices(current_system_name), False


def try_load_texture(file_name, folder, filtering="bilinear"):
    if not folder.exists():
        return None

    try:
        return load_texture(file_name, folder=folder, filtering=filtering)
    except Exception as error:
        print(f"[Space RPG] Texture load failed for {file_name}: {error}")
        return None


def try_load_model(file_name, folder):
    if not folder.exists():
        return None

    try:
        return load_model(file_name, folder=folder)
    except Exception as error:
        print(f"[Space RPG] Model load failed for {file_name}: {error}")
        return None


def resolve_app_icon():
    local_icon = URSINA_REPO_TEXTURES / "ursina.ico"
    if local_icon.exists():
        return str(local_icon.resolve())
    return "textures/ursina.ico"


def disable_ursina_editor_gui():
    # Ursina 8.3.0 still constructs editor widgets even when they are disabled.
    # In this project the editor cog texture is not needed and can crash startup.
    class DisabledEditorUI:
        enabled = False
        children = []

    window.make_editor_gui = lambda: setattr(window, "editor_ui", DisabledEditorUI())


disable_ursina_editor_gui()
app = Ursina(
    icon=resolve_app_icon(),
    development_mode=False,
    editor_ui_enabled=False,
    fullscreen=False,
    show_ursina_splash=False,
)

hull_panel_texture = try_load_texture("tech_panel_dark.png", GENERATED_ASSETS_ROOT)
console_panel_texture = try_load_texture("console_panel_dark.png", GENERATED_ASSETS_ROOT)
ship_panel_texture = hull_panel_texture or try_load_texture("noise.png", URSINA_REPO_TEXTURES)
console_screen_texture = console_panel_texture or try_load_texture("vertical_gradient.png", URSINA_REPO_TEXTURES)
skybox_texture = try_load_texture("skybox.png", KENNEY_SPRITES)
crosshair_texture = try_load_texture("crosshair.png", KENNEY_SPRITES, filtering="nearest")
npc_crosshair_texture = try_load_texture("hit.png", KENNEY_SPRITES, filtering="nearest")
ui_button_base_texture = try_load_texture("button_rectangle_flat.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
ui_button_hot_texture = try_load_texture("button_rectangle_depth_gradient.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
ui_button_selected_texture = try_load_texture("button_rectangle_depth_gloss.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
ui_icon_circle_texture = try_load_texture("icon_circle.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
ui_icon_square_texture = try_load_texture("icon_square.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
ui_icon_check_texture = try_load_texture("icon_checkmark.png", KENNEY_UI_BLUE_DOUBLE, filtering="nearest")
radial_gradient_texture = try_load_texture("radial_gradient.png", URSINA_REPO_TEXTURES)
vignette_texture = try_load_texture("vignette.png", URSINA_REPO_TEXTURES)
droid_model_asset = try_load_model("enemy-flying.glb", KENNEY_MODELS)
r2_droid_model_asset = try_load_model("r2_droid.glb", POLY_PIZZA_ROOT)
poly_pizza_robot_model_asset = try_load_model("robot_lowpoly.glb", POLY_PIZZA_ROOT)
rigged_simple_model_asset = try_load_model("RiggedSimple.glb", KHRONOS_RIGGEDSIMPLE)
cesium_man_model_asset = try_load_model("CesiumMan.glb", KHRONOS_CESIUMMAN)
technician_model_asset = poly_pizza_robot_model_asset or r2_droid_model_asset or rigged_simple_model_asset or cesium_man_model_asset

UI_BUTTON_BASE_COLOR = C(54, 98, 160, 255) if ui_button_base_texture else C(20, 50, 92, 238)
UI_BUTTON_SELECTED_COLOR = C(72, 122, 190, 255) if ui_button_selected_texture else C(42, 104, 176, 246)
UI_BUTTON_HOT_COLOR = C(86, 146, 214, 255) if ui_button_hot_texture else C(64, 132, 205, 248)
UI_BUTTON_TEXT_COLOR = C(230, 238, 255)
UI_BUTTON_ACTIVE_TEXT_COLOR = C(248, 250, 255)


def style_panel(entity, base_color, texture_override=None):
    if not entity:
        return
    entity.color = base_color
    entity.texture = texture_override or console_panel_texture or ui_button_base_texture


def refresh_standard_ui_button_text(button):
    if not button:
        return
    legacy_value = getattr(button, "_legacy_text_size", 0.36)
    target_size = ui_scale_manager.button_text_size(legacy_value)
    button.text_size = target_size
    button.highlight_text_size = target_size
    if button.text_entity:
        apply_text_role(button.text_entity, "body", multiplier=0.96, color_value=UI_BUTTON_TEXT_COLOR, font_value=BODY_FONT)
        button.text_entity.origin = (0, 0)
        button.text_entity.position = (0, -0.01, -0.01)


def build_standard_ui_button(parent, label, position, scale, button_index, on_click=None, text_size=0.82):
    # Ursina Button interprets text_size as absolute world scale multiplier.
    # Route all button typography through a single scale manager.
    button_text_size = ui_scale_manager.button_text_size(text_size)
    button = Button(
        parent=parent,
        text=label,
        model="quad",
        position=position,
        scale=scale,
        color=UI_BUTTON_BASE_COLOR,
        texture=ui_button_base_texture or console_panel_texture,
        collider="box",
        text_color=UI_BUTTON_TEXT_COLOR,
        text_origin=(0, 0),
        text_size=button_text_size,
        highlight_text_size=button_text_size,
        highlight_scale=1,
        pressed_scale=0.985,
    )
    button.button_index = button_index
    button._legacy_text_size = float(text_size)
    button.base_color = UI_BUTTON_BASE_COLOR
    button.selected_color = UI_BUTTON_SELECTED_COLOR
    button.hot_color = UI_BUTTON_HOT_COLOR
    button.base_texture = ui_button_base_texture or console_panel_texture
    button.selected_texture = ui_button_selected_texture or button.base_texture
    button.hot_texture = ui_button_hot_texture or button.selected_texture
    button.highlight_color = button.base_color
    button.pressed_color = button.base_color
    if on_click:
        button.on_click = on_click
    if button.text_entity:
        refresh_standard_ui_button_text(button)
    return button


def set_standard_ui_button_state(button, state):
    if state == "hot":
        button.color = button.hot_color
        button.texture = button.hot_texture
        if button.text_entity:
            button.text_entity.color = UI_BUTTON_ACTIVE_TEXT_COLOR
        return

    if state == "selected":
        button.color = button.selected_color
        button.texture = button.selected_texture
        if button.text_entity:
            button.text_entity.color = UI_BUTTON_ACTIVE_TEXT_COLOR
        return

    button.color = button.base_color
    button.texture = button.base_texture
    if button.text_entity:
        button.text_entity.color = UI_BUTTON_TEXT_COLOR


window.title = "Space RPG Prototype"
window.color = C(2, 4, 10)
window.borderless = False
if hasattr(window, "exit_button"):
    window.exit_button.visible = False
Text.default_font = BODY_FONT
Text.default_monospace_font = TECH_FONT
# Reference baseline for Text entities; actual role sizes are assigned centrally.
Text.size = 0.020
Text.default_resolution = 128


def apply_ui_scale():
    global ui_scale_factor
    engine_base = getattr(builtins, "base", None)
    if not engine_base or not getattr(engine_base, "win", None):
        return

    width, height = [max(1, int(value)) for value in engine_base.win.getSize()]
    ui_scale_manager.update(width, height)
    # Ursina UI root is internally scaled (~20). Normalize against it so authored
    # UI coordinates stay in one design grid across all resolutions.
    ui_canvas_base = 1.0 / max(0.0001, float(camera.ui.scale_x))
    target_scale = ui_scale_manager.uniform_scale * ui_canvas_base
    ui_scale_factor = target_scale
    alive_roots = []
    for root in ui_roots:
        if not root or not hasattr(root, "parent"):
            continue
        base_scale = getattr(root, "_ui_base_scale", Vec3(1, 1, 1))
        root.scale = base_scale * target_scale
        alive_roots.append(root)
    ui_roots[:] = alive_roots
    refresh_ui_layouts()


def make_ui_root(enabled=True):
    root = Entity(parent=camera.ui, enabled=enabled)
    root._ui_base_scale = Vec3(root.scale_x, root.scale_y, root.scale_z)
    ui_roots.append(root)
    apply_ui_scale()
    return root


def monitor_label(index):
    if not DISPLAY_MONITORS:
        return "\u041c\u043e\u043d\u0438\u0442\u043e\u0440 1"
    index = int(clamp(index, 0, len(DISPLAY_MONITORS) - 1))
    return DISPLAY_MONITORS[index].get("label", f"\u041c\u043e\u043d\u0438\u0442\u043e\u0440 {index + 1}")


def monitor_short_label(index):
    if not DISPLAY_MONITORS:
        return "\u21161"
    index = int(clamp(index, 0, len(DISPLAY_MONITORS) - 1))
    monitor = DISPLAY_MONITORS[index]
    return f"\u2116{index + 1} ({monitor['width']}x{monitor['height']})"


def move_native_window_to_monitor_origin(monitor_index):
    try:
        engine_base = getattr(builtins, "base", None)
        if not engine_base or not getattr(engine_base, "win", None) or not DISPLAY_MONITORS:
            return

        monitor_index = int(clamp(monitor_index, 0, len(DISPLAY_MONITORS) - 1))
        monitor = DISPLAY_MONITORS[monitor_index]
        win_handle = engine_base.win.getWindowHandle()
        hwnd = int(win_handle.getIntHandle()) if win_handle and hasattr(win_handle, "getIntHandle") else 0
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        user32.SetWindowPos(
            hwnd,
            0,
            int(monitor["x"]),
            int(monitor["y"]),
            0,
            0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
        )
    except Exception as error:
        print(f"[Space RPG] Native move-to-origin failed: {error}")


def recenter_native_window_on_monitor(monitor_index):
    try:
        engine_base = getattr(builtins, "base", None)
        if not engine_base or not getattr(engine_base, "win", None) or not DISPLAY_MONITORS:
            return

        monitor_index = int(clamp(monitor_index, 0, len(DISPLAY_MONITORS) - 1))
        monitor = DISPLAY_MONITORS[monitor_index]
        win_handle = engine_base.win.getWindowHandle()
        hwnd = int(win_handle.getIntHandle()) if win_handle and hasattr(win_handle, "getIntHandle") else 0
        if not hwnd:
            return

        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return

        outer_width = max(1, rect.right - rect.left)
        outer_height = max(1, rect.bottom - rect.top)
        max_x = int(monitor["x"] + max(0, monitor["width"] - outer_width))
        max_y = int(monitor["y"] + max(0, monitor["height"] - outer_height))
        target_x = int(monitor["x"] + (monitor["width"] - outer_width) // 2)
        target_y = int(monitor["y"] + (monitor["height"] - outer_height) // 2)
        target_x = int(clamp(target_x, monitor["x"], max_x))
        target_y = int(clamp(target_y, monitor["y"], max_y))
        user32.SetWindowPos(hwnd, 0, target_x, target_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
    except Exception as error:
        print(f"[Space RPG] Native recenter failed: {error}")


def resolve_display_geometry(monitor, mode, window_scale_index):
    monitor_x = int(monitor["x"])
    monitor_y = int(monitor["y"])
    monitor_width = max(1, int(monitor["width"]))
    monitor_height = max(1, int(monitor["height"]))

    if mode in ("fullscreen", "borderless"):
        return monitor_x, monitor_y, monitor_width, monitor_height

    scale_index = int(clamp(window_scale_index, 0, len(WINDOWED_SCALE_PRESETS) - 1))
    scale = WINDOWED_SCALE_PRESETS[scale_index]
    width = max(960, int(monitor_width * scale))
    height = max(540, int(monitor_height * scale))

    width = min(width, max(960, monitor_width - 40))
    height = min(height, max(540, monitor_height - 40))
    if width % 2:
        width -= 1
    if height % 2:
        height -= 1

    origin_x = monitor_x + max(0, (monitor_width - width) // 2)
    origin_y = monitor_y + max(0, (monitor_height - height) // 2)
    return origin_x, origin_y, width, height


def window_profile_label():
    if not DISPLAY_MONITORS:
        return "Авто"

    monitor_index = int(clamp(display_settings["monitor_index"], 0, len(DISPLAY_MONITORS) - 1))
    monitor = DISPLAY_MONITORS[monitor_index]
    mode = display_settings["window_mode"]
    if mode != "windowed":
        return "Авто"

    scale_index = int(clamp(display_settings["window_scale_index"], 0, len(WINDOWED_SCALE_PRESETS) - 1))
    scale_percent = int(WINDOWED_SCALE_PRESETS[scale_index] * 100)
    return f"{scale_percent}%"


def apply_display_settings():
    monitor_index = int(clamp(display_settings["monitor_index"], 0, max(0, len(DISPLAY_MONITORS) - 1)))
    monitor = DISPLAY_MONITORS[monitor_index]
    mode = display_settings["window_mode"]
    origin_x, origin_y, width, height = resolve_display_geometry(
        monitor,
        mode,
        display_settings["window_scale_index"],
    )

    try:
        apply_window_monitor_and_capture(origin_x, origin_y, width, height, mode)
    except Exception as error:
        print(f"[Space RPG] Display settings failed: {error}")

    reset_mouse_motion()


def apply_window_monitor_and_capture(origin_x, origin_y, width=None, height=None, mode="windowed"):
    """Move the OS window first, then re-apply foreground and mouse confinement."""
    global window_event_suppressed_until

    is_fullscreen = mode == "fullscreen"
    is_borderless = mode == "borderless"
    props = WindowProperties()
    props.setFullscreen(is_fullscreen)
    props.setUndecorated(is_borderless)
    props.setOrigin(int(origin_x), int(origin_y))
    props.setForeground(True)
    if width and height:
        props.setSize(int(width), int(height))

    if wants_gameplay_mouse_capture():
        props.setMouseMode(WindowProperties.M_confined)
        props.setCursorHidden(True)
        set_ursina_mouse_capture_state(True)
    else:
        props.setMouseMode(WindowProperties.M_absolute)
        props.setCursorHidden(False)
        set_ursina_mouse_capture_state(False)

    window_event_suppressed_until = py_time.monotonic() + 0.20
    base.win.requestProperties(props)
    monitor_index = int(clamp(display_settings["monitor_index"], 0, max(0, len(DISPLAY_MONITORS) - 1)))
    if mode == "windowed":
        invoke(recenter_native_window_on_monitor, monitor_index, delay=0.04)
        invoke(recenter_native_window_on_monitor, monitor_index, delay=0.16)
    elif mode == "borderless":
        invoke(move_native_window_to_monitor_origin, monitor_index, delay=0.04)
        invoke(move_native_window_to_monitor_origin, monitor_index, delay=0.16)

    # Panda3D applies window properties asynchronously. Re-confirm confinement
    # after the move/focus events have been processed by the window system.
    schedule_mouse_recapture(delays=(0.05, 0.16, 0.34), foreground=True)
    invoke(normalize_ui_camera, delay=0.08)
    invoke(normalize_ui_camera, delay=0.22)


def normalize_ui_camera():
    try:
        # Do not touch camera.ui.scale or camera.ui_lens here. Ursina owns that
        # transform; changing it globally resizes maps, dialogue, pause and HUD.
        width, height = [max(1, int(value)) for value in base.win.getSize()]
        camera.set_shader_input("window_size", (width, height))
        apply_ui_scale()
    except Exception as error:
        print(f"[Space RPG] UI camera normalize failed: {error}")


def set_os_cursor_hidden(is_hidden):
    try:
        global window_event_suppressed_until
        props = WindowProperties()
        props.setCursorHidden(bool(is_hidden))
        props.setMouseMode(WindowProperties.M_confined if is_hidden else WindowProperties.M_absolute)
        window_event_suppressed_until = py_time.monotonic() + 0.12
        base.win.requestProperties(props)
        set_ursina_mouse_capture_state(bool(is_hidden))
    except Exception as error:
        print(f"[Space RPG] Cursor visibility failed: {error}")


def should_lock_mouse():
    return True


def wants_gameplay_mouse_capture():
    return "player" in globals() and not is_any_overlay_open()


def set_ursina_mouse_capture_state(is_captured):
    # Avoid mouse.locked's setter here: it sends its own WindowProperties request.
    # We already send a Panda request with the selected monitor origin/foreground.
    mouse._locked = bool(is_captured)
    mouse._locked_mouse_last_frame = True
    mouse.visible = not is_captured


def request_mouse_mode(is_captured, foreground=False):
    global window_event_suppressed_until

    props = WindowProperties()
    if foreground:
        props.setForeground(True)
    props.setMouseMode(WindowProperties.M_confined if is_captured else WindowProperties.M_absolute)
    props.setCursorHidden(bool(is_captured))
    window_event_suppressed_until = py_time.monotonic() + 0.12
    base.win.requestProperties(props)
    set_ursina_mouse_capture_state(is_captured)


def capture_mouse_for_gameplay(foreground=True):
    request_mouse_mode(True, foreground=foreground)
    reset_mouse_motion()


def release_mouse_for_ui():
    request_mouse_mode(False, foreground=False)
    reset_mouse_motion()


def _recapture_mouse_task(request_id, foreground):
    if request_id != mouse_capture_request_id:
        return Task.done

    if wants_gameplay_mouse_capture():
        capture_mouse_for_gameplay(foreground=foreground)
    else:
        release_mouse_for_ui()
    return Task.done


def _confirm_mouse_mode_task(request_id, foreground):
    if request_id != mouse_capture_request_id:
        return Task.done

    try:
        current_props = base.win.getProperties()
        wants_capture = wants_gameplay_mouse_capture()
        current_mode = current_props.getMouseMode()
        cursor_hidden = current_props.getCursorHidden()
        if wants_capture and (current_mode != WindowProperties.M_confined or not cursor_hidden):
            capture_mouse_for_gameplay(foreground=foreground)
        elif not wants_capture and (current_mode != WindowProperties.M_absolute or cursor_hidden):
            release_mouse_for_ui()
    except Exception as error:
        print(f"[Space RPG] Mouse capture confirmation failed: {error}")
    return Task.done


def schedule_mouse_recapture(delays=(0.05,), foreground=True):
    global mouse_capture_request_id
    engine_base = getattr(builtins, "base", None)
    if not engine_base or not getattr(engine_base, "win", None):
        return

    mouse_capture_request_id += 1
    request_id = mouse_capture_request_id
    for index, delay in enumerate(delays):
        engine_base.taskMgr.doMethodLater(
            delay,
            _recapture_mouse_task,
            f"space-rpg-recapture-mouse-{request_id}-{index}",
            extraArgs=[request_id, foreground],
        )
    engine_base.taskMgr.doMethodLater(
        max(delays) + 0.08,
        _confirm_mouse_mode_task,
        f"space-rpg-confirm-mouse-mode-{request_id}",
        extraArgs=[request_id, foreground],
    )


def apply_mouse_lock_policy():
    if "player" not in globals():
        return
    if wants_gameplay_mouse_capture():
        capture_mouse_for_gameplay(foreground=True)
        return
    release_mouse_for_ui()


def handle_window_event(_window):
    global mouse_focus_restore_timer

    now = py_time.monotonic()
    if now < window_event_suppressed_until or now < mouse_focus_restore_timer:
        return

    mouse_focus_restore_timer = now + 0.45
    normalize_ui_camera()
    if wants_gameplay_mouse_capture():
        schedule_mouse_recapture(delays=(0.02, 0.12, 0.28), foreground=True)


def quit_game():
    try:
        release_mouse_for_ui()
    except Exception:
        pass

    try:
        base.userExit()
    except SystemExit:
        raise
    except Exception:
        pass

    raise SystemExit(0)


print(f"[Space RPG] Project root: {PROJECT_ROOT}")
print(f"[Space RPG] Assets folder: {ASSETS_ROOT}")


# 3D coordinate guide:
# X moves left and right across the room.
# Y moves up and down.
# Z moves forward and backward through the room.
# For the sword attached to the camera, these same axes are local to the view.


def build_space_sky():
    if skybox_texture:
        Sky(texture=skybox_texture, color=C(34, 44, 68))
    else:
        Entity(
            model="sphere",
            scale=420,
            color=C(2, 3, 8),
            double_sided=True,
        )

    for _ in range(140):
        direction = Vec3(
            random.uniform(-1, 1),
            random.uniform(-1, 1),
            random.uniform(-1, 1),
        ).normalized()

        Entity(
            model="sphere",
            position=direction * random.uniform(160, 210),
            scale=random.uniform(0.12, 0.35),
            color=C(180, 210, 255, random.randint(55, 160)),
        )


def build_ship_interior():
    metal_dark = C(16, 19, 28)
    metal_mid = C(28, 34, 48)

    floor = Entity(
        model="cube",
        position=(0, -1, 0),
        scale=(ROOM_HALF_SIZE * 2, 0.5, ROOM_HALF_SIZE * 2),
        color=metal_dark,
        texture=ship_panel_texture,
        texture_scale=(10, 10),
        collider="box",
    )

    back_wall = Entity(
        model="cube",
        position=(0, ROOM_HEIGHT / 2 - 1, ROOM_HALF_SIZE),
        scale=(ROOM_HALF_SIZE * 2, ROOM_HEIGHT, 0.5),
        color=metal_mid,
        texture=ship_panel_texture,
        texture_scale=(8, 2),
        collider="box",
    )

    front_wall = Entity(
        model="cube",
        position=(0, ROOM_HEIGHT / 2 - 1, -ROOM_HALF_SIZE),
        scale=(ROOM_HALF_SIZE * 2, ROOM_HEIGHT, 0.5),
        color=metal_mid,
        texture=ship_panel_texture,
        texture_scale=(8, 2),
        collider="box",
    )

    left_wall = Entity(
        model="cube",
        position=(-ROOM_HALF_SIZE, ROOM_HEIGHT / 2 - 1, 0),
        scale=(0.5, ROOM_HEIGHT, ROOM_HALF_SIZE * 2),
        color=metal_mid,
        texture=ship_panel_texture,
        texture_scale=(8, 2),
        collider="box",
    )

    right_wall = Entity(
        model="cube",
        position=(ROOM_HALF_SIZE, ROOM_HEIGHT / 2 - 1, 0),
        scale=(0.5, ROOM_HEIGHT, ROOM_HALF_SIZE * 2),
        color=metal_mid,
        texture=ship_panel_texture,
        texture_scale=(8, 2),
        collider="box",
    )

    return floor, back_wall, front_wall, left_wall, right_wall


def build_crosshair(parent=None):
    crosshair_parent = parent or camera.ui
    default_crosshair = Entity(
        parent=crosshair_parent,
        model="quad",
        texture=crosshair_texture,
        scale=0.022 if crosshair_texture else 0.014,
        color=C(135, 210, 255, 160),
    )

    npc_hover_icon = Entity(
        parent=crosshair_parent,
        model="quad",
        texture=npc_crosshair_texture,
        scale=0.016 if npc_crosshair_texture else 0.010,
        color=C(90, 255, 210, 180),
        enabled=False,
    )

    return default_crosshair, npc_hover_icon


def is_any_overlay_open():
    return (
        ("galaxy_map" in globals() and galaxy_map.is_open)
        or ("dialogue_ui" in globals() and dialogue_ui.is_open)
        or ("pause_menu" in globals() and pause_menu.is_open)
    )


def toggle_crosshair(is_on_npc):
    if is_any_overlay_open():
        default_crosshair.enabled = False
        npc_crosshair.enabled = False
        return

    default_crosshair.enabled = not is_on_npc
    npc_crosshair.enabled = is_on_npc


def show_map_message():
    global map_message_timer
    map_message_timer = MAP_MESSAGE_DURATION
    set_text_block_state(map_message_text, map_message_panel, True)


def reset_saber_pose():
    global saber_is_swinging
    saber_holder.animate_position((0.45, -0.45, 0.65), duration=0.12)
    saber_holder.animate_rotation((25, -15, -8), duration=0.12)

    def unlock_saber():
        global saber_is_swinging
        saber_is_swinging = False

    invoke(unlock_saber, delay=0.12)


def swing_saber():
    global saber_is_swinging
    if saber_is_swinging or is_any_overlay_open():
        return

    saber_is_swinging = True
    saber_holder.animate_position((0.3, -0.35, 0.45), duration=0.08)
    saber_holder.animate_rotation((65, -25, 8), duration=0.08)
    invoke(reset_saber_pose, delay=0.08)


def current_target(distance=3.5):
    return raycast(
        camera.world_position,
        camera.forward,
        distance=distance,
        ignore=raycast_ignore,
    )


def make_route_line(parent, start, end, tint, thickness=0.004, z=0):
    start_v = Vec2(start[0], start[1])
    end_v = Vec2(end[0], end[1])
    delta = end_v - start_v
    length = delta.length()
    angle = degrees(atan2(delta.y, delta.x))

    return Entity(
        parent=parent,
        model="quad",
        position=(start_v.x, start_v.y, z),
        origin=(-0.5, 0),
        scale=(length, thickness),
        rotation_z=angle,
        color=tint,
    )


def build_route_polyline(parent, points, color_value=(0.45, 0.9, 1.0, 0.95), thickness=3.0, name="route_line"):
    """Draw one graph route as a true polyline: moveTo first node, drawTo each next node."""
    if not points or len(points) < 2:
        return None

    lines = LineSegs(name)
    lines.setColor(*color_value)
    lines.setThickness(thickness)
    lines.moveTo(points[0])
    for point in points[1:]:
        lines.drawTo(point)

    node_path = parent.attachNewNode(lines.create())
    node_path.setTransparency(TransparencyAttrib.MAlpha)
    node_path.setDepthTest(False)
    node_path.setDepthWrite(False)
    return node_path


def make_holo_ellipse(parent, center, radius_x, radius_y, tint, thickness=0.002, z=0, segments=18, rotation=0):
    points = []
    for index in range(segments):
        angle = (index / segments) * 360
        angle_rad = angle * 3.14159265 / 180
        x = cos(angle_rad) * radius_x
        y = sin(angle_rad) * radius_y
        rotated_x = x * cos(rotation) - y * sin(rotation)
        rotated_y = x * sin(rotation) + y * cos(rotation)
        points.append((center[0] + rotated_x, center[1] + rotated_y))

    parts = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        parts.append(make_route_line(parent, start, end, tint=tint, thickness=thickness, z=z))
    return parts


def set_wrapped_text(text_entity, value, wrap):
    """Ursina can fail on Text(wordwrap=...) during __init__, so wrap after assigning text."""
    text_entity.text = value
    text_entity.wordwrap = wrap


def set_text_block_state(text_entity, panel_entity, enabled):
    text_entity.enabled = enabled
    panel_entity.enabled = enabled


def set_controls_hint_state(enabled):
    controls_hint.enabled = enabled
    controls_panel.enabled = enabled


def ui_panel_position(panel_entity, local_x, local_y, z=0):
    return Vec3(
        panel_entity.x + local_x * panel_entity.scale_x,
        panel_entity.y + local_y * panel_entity.scale_y,
        z,
    )


def capture_window_position():
    # Do not pin the OS window position. The player may move the game to another monitor.
    return None


def restore_window_position(saved_position):
    # Intentionally disabled: forcing window.position caused the game to jump back to monitor 1.
    return


def reset_mouse_motion():
    try:
        mouse.velocity = Vec3(0, 0, 0)
        mouse.delta = Vec3(0, 0, 0)
        mouse.prev_x = mouse.x
        mouse.prev_y = mouse.y
    except Exception:
        pass


def center_mouse_pointer():
    # Do not warp the OS cursor. On multi-monitor setups Panda/Ursina can pull
    # the window back to the primary monitor when the cursor is forcibly centered.
    reset_mouse_motion()


def stabilize_first_person_restore():
    if getattr(player, "_restore_stabilize_frames", 0) <= 0:
        return

    player.rotation_y = getattr(player, "_stored_rotation_y", player.rotation_y)
    player.camera_pivot.rotation_x = getattr(player, "_stored_camera_rotation_x", player.camera_pivot.rotation_x)
    center_mouse_pointer()
    reset_mouse_motion()
    restore_window_position(getattr(player, "_stored_window_position", None))
    player._restore_stabilize_frames -= 1


def freeze_first_person():
    if getattr(player, "_map_frozen", False):
        return

    player._map_frozen = True
    player._restore_stabilize_frames = 0
    player._stored_speed = player.speed
    player._stored_gravity = player.gravity
    player._stored_mouse_sensitivity = Vec2(player.mouse_sensitivity[0], player.mouse_sensitivity[1])
    player._stored_rotation_y = player.rotation_y
    player._stored_camera_rotation_x = player.camera_pivot.rotation_x
    player._stored_window_position = capture_window_position()
    player.speed = 0
    player.gravity = 0
    player.mouse_sensitivity = Vec2(0, 0)
    player.cursor.enabled = False
    release_mouse_for_ui()
    reset_mouse_motion()
    restore_window_position(player._stored_window_position)
    invoke(restore_window_position, player._stored_window_position, delay=0)


def restore_first_person():
    if not getattr(player, "_map_frozen", False):
        return

    player._map_frozen = False
    player.speed = getattr(player, "_stored_speed", 5)
    player.gravity = getattr(player, "_stored_gravity", 0.5)
    player.rotation_y = getattr(player, "_stored_rotation_y", player.rotation_y)
    player.camera_pivot.rotation_x = getattr(player, "_stored_camera_rotation_x", player.camera_pivot.rotation_x)
    player._restore_stabilize_frames = 0
    player.cursor.enabled = False
    center_mouse_pointer()
    player.mouse_sensitivity = getattr(player, "_stored_mouse_sensitivity", Vec2(40, 40))
    capture_mouse_for_gameplay(foreground=True)
    schedule_mouse_recapture(delays=(0.05, 0.14, 0.30), foreground=True)
    reset_mouse_motion()
    restore_window_position(getattr(player, "_stored_window_position", None))
    invoke(reset_mouse_motion, delay=0)
    invoke(restore_window_position, getattr(player, "_stored_window_position", None), delay=0)


class DialogueUI:
    def __init__(self):
        self.is_open = False
        self.stage = 0
        self.active_npc = None
        self.active_brain = None
        self.speaker_name = "Собеседник"
        self.selected_choice_index = 0
        self.choice_entries = []
        self.choices = []

        self.root = make_ui_root(enabled=False)
        self.subtitle_panel = Entity(
            parent=self.root,
            model="quad",
            position=(0.0, -0.350),
            scale=(1.28, 0.220),
            color=C(8, 14, 28, 234),
            texture=console_panel_texture,
        )
        style_panel(self.subtitle_panel, C(8, 14, 28, 234))
        self.subtitle_edge = Entity(
            parent=self.root,
            model="quad",
            position=(0.0, -0.246),
            scale=(1.30, 0.004),
            color=C(102, 168, 225, 140),
        )
        self.name_plate = Entity(
            parent=self.root,
            model="quad",
            position=(-0.49, -0.246),
            scale=(0.30, 0.052),
            color=C(24, 54, 94, 230),
        )
        self.name_text = Text(
            parent=self.root,
            text="",
            position=(-0.60, -0.263),
            scale=0.66,
            color=C(165, 220, 255),
            font=TITLE_FONT,
        )
        apply_text_role(self.name_text, "subtitle", multiplier=1.08, color_value=C(165, 220, 255), font_value=TITLE_FONT)
        self.body_text = Text(
            parent=self.root,
            text="",
            position=(-0.60, -0.322),
            scale=0.52,
            color=C(232, 240, 255),
            font=BODY_FONT,
            line_height=1.0,
        )
        apply_text_role(self.body_text, "body", multiplier=1.00, color_value=C(232, 240, 255), font_value=BODY_FONT, line_height=1.08)
        self.body_wrap = 62

        self.response_panel = Entity(
            parent=self.root,
            model="quad",
            position=(0.58, 0.00),
            scale=(0.34, 0.44),
            color=C(10, 18, 34, 240),
            texture=console_panel_texture,
        )
        style_panel(self.response_panel, C(10, 18, 34, 240))
        self.response_edge = Entity(
            parent=self.root,
            model="quad",
            position=(0.58, 0.215),
            scale=(0.34, 0.004),
            color=C(102, 168, 225, 140),
        )
        self.response_icon = Entity(
            parent=self.response_panel,
            model="quad",
            position=(-0.39, 0.42, -0.01),
            scale=(0.08, 0.08),
            texture=ui_icon_square_texture or ui_icon_circle_texture,
            color=C(130, 206, 255, 160),
        )
        for index in range(5):
            button_y = 0.148 - index * 0.082
            choice_button = build_standard_ui_button(
                parent=self.response_panel,
                label="",
                position=(0.0, button_y),
                scale=(0.82, 0.068),
                button_index=index,
                on_click=Func(self.choose, index),
                text_size=0.42,
            )
            choice_button.choice_index = index
            choice_button.enabled = False
            self.choice_entries.append(choice_button)
        register_ui_layout(self._apply_layout)
        self._apply_layout()

    def _apply_layout(self):
        safe_left, safe_right, safe_top, safe_bottom = ui_scale_manager.safe_rect()
        safe_width = safe_right - safe_left
        safe_height = safe_top - safe_bottom

        subtitle_width = clamp(safe_width, 1.18, 1.48)
        subtitle_height = clamp(0.20 + ui_scale_manager.narrow_factor * 0.04, 0.20, 0.25)
        subtitle_center_x = (safe_left + safe_right) * 0.5
        subtitle_center_y = safe_bottom + subtitle_height * 0.56
        self.subtitle_panel.position = (subtitle_center_x, subtitle_center_y)
        self.subtitle_panel.scale = (subtitle_width, subtitle_height)
        self.subtitle_edge.position = (subtitle_center_x, subtitle_center_y + subtitle_height * 0.47)
        self.subtitle_edge.scale = (subtitle_width, 0.004)

        self.name_plate.position = (safe_left + 0.16, subtitle_center_y + subtitle_height * 0.46)
        self.name_plate.scale = (0.30, 0.048)
        self.name_text.position = (safe_left + 0.04, subtitle_center_y + subtitle_height * 0.32)
        self.body_text.position = (safe_left + 0.04, subtitle_center_y + subtitle_height * 0.02)
        apply_text_role(self.name_text, "subtitle", multiplier=1.08)
        apply_text_role(self.body_text, "body", multiplier=1.0, line_height=1.08)

        response_width = ui_scale_manager.panel_width(0.34, 0.30, 0.40)
        response_height = clamp(safe_height * 0.52, 0.36, 0.46)
        response_center_x = safe_right - response_width * 0.52
        response_center_y = (safe_top + safe_bottom) * 0.08
        self.response_panel.position = (response_center_x, response_center_y)
        self.response_panel.scale = (response_width, response_height)
        self.response_edge.position = (response_center_x, response_center_y + response_height * 0.49)
        self.response_edge.scale = (response_width, 0.004)
        self.response_icon.position = (-0.39, 0.42, -0.01)
        self.response_icon.scale = (0.08, 0.08)

        choice_height = clamp(0.064 - ui_scale_manager.narrow_factor * 0.007, 0.056, 0.066)
        choice_step = clamp(choice_height + 0.010, 0.065, 0.075)
        start_y = response_height * 0.34
        for index, choice_button in enumerate(self.choice_entries):
            choice_button.scale = (0.84, choice_height)
            choice_button.position = (0.0, start_y - index * choice_step)
            refresh_standard_ui_button_text(choice_button)

        self.body_wrap = int(clamp(54 + safe_width * 12, 52, 72))
        if hasattr(self.body_text, "raw_text"):
            self.body_text.wordwrap = self.body_wrap

    def open(self, speaker_entity):
        if self.is_open or map_open_queued or galaxy_map.is_open:
            return

        self.is_open = True
        self.stage = 0
        self.active_npc = speaker_entity
        self.active_brain = getattr(speaker_entity, "npc_brain", None)
        self.speaker_name = getattr(speaker_entity, "npc_name", "Собеседник")
        self.selected_choice_index = 0
        self.root.enabled = True
        self._apply_layout()
        self.name_text.text = self.speaker_name.upper()
        if self.active_brain:
            opening_line, choices = self.active_brain.open_dialogue(galaxy_map.current_system_name)
        else:
            opening_line = "Привет. Я на связи."
            choices = [
                {"id": "greet", "label": "Привет."},
                {"id": "status", "label": "Как дела?"},
                {"id": "bye", "label": "Пока."},
            ]

        set_wrapped_text(self.body_text, f"{self.speaker_name}: {opening_line}", self.body_wrap)
        self._set_choices(choices)
        interaction_text.enabled = False
        interaction_panel.enabled = False
        set_controls_hint_state(False)
        set_text_block_state(map_message_text, map_message_panel, False)
        freeze_first_person()
        default_crosshair.enabled = False
        npc_crosshair.enabled = False

    def _set_choices(self, choices):
        self.choices = choices

        for index, choice_button in enumerate(self.choice_entries):
            is_active = index < len(choices)
            choice_button.enabled = is_active
            choice_button.disabled = not is_active
            if not is_active:
                choice_button.text = ""
                continue

            choice_button.text = f"{index + 1}. {choices[index]['label']}"
            if choice_button.text_entity:
                apply_text_role(choice_button.text_entity, "body", multiplier=0.92, color_value=UI_BUTTON_TEXT_COLOR, font_value=BODY_FONT)
                choice_button.text_entity.origin = (0, 0)
                choice_button.text_entity.position = (0, -0.01, -0.01)

        self._refresh_choice_highlight()

    def _refresh_choice_highlight(self):
        hovered = mouse.hovered_entity if self.is_open and mouse.visible else None

        for index, choice_button in enumerate(self.choice_entries):
            if not choice_button.enabled:
                continue

            if hovered == choice_button:
                set_standard_ui_button_state(choice_button, "hot")
            elif index == self.selected_choice_index:
                set_standard_ui_button_state(choice_button, "selected")
            else:
                set_standard_ui_button_state(choice_button, "base")

    def choose(self, index):
        if not self.is_open or index >= len(self.choices):
            return

        choice = self.choices[index]
        choice_id = choice.get("id")

        if self.active_brain:
            reply_text, next_choices, should_finish = self.active_brain.respond(choice_id, galaxy_map.current_system_name)
        else:
            reply_text = "Канал чист. Обращайся."
            next_choices = [
                {"id": "greet", "label": "Привет."},
                {"id": "bye", "label": "Пока."},
            ]
            should_finish = False

        if should_finish:
            self.close()
            return

        set_wrapped_text(self.body_text, f"Ты: {choice['label']}\n{self.speaker_name}: {reply_text}", self.body_wrap)
        self.stage = 0
        self.selected_choice_index = 0
        self._set_choices(next_choices)

    def close(self):
        if not self.is_open:
            return

        self.is_open = False
        self.stage = 0
        self.active_npc = None
        self.active_brain = None
        self.choices = []
        self.selected_choice_index = 0
        self.root.enabled = False
        restore_first_person()
        set_controls_hint_state(True)
        default_crosshair.enabled = True
        npc_crosshair.enabled = False
        interaction_text.enabled = False
        interaction_panel.enabled = False

    def update(self):
        if not self.is_open:
            return

        hovered = mouse.hovered_entity
        if hovered in self.choice_entries and hovered.enabled:
            self.selected_choice_index = hovered.choice_index

        self._refresh_choice_highlight()

    def input(self, key):
        if not self.is_open:
            return False

        if key == "escape":
            self.close()
            return True

        if key in ("up arrow", "w"):
            self.selected_choice_index = max(0, self.selected_choice_index - 1)
            self._refresh_choice_highlight()
            return True

        if key in ("down arrow", "s"):
            self.selected_choice_index = min(len(self.choices) - 1, self.selected_choice_index + 1)
            self._refresh_choice_highlight()
            return True

        if key in ("1", "2", "3", "4", "5"):
            chosen_index = int(key) - 1
            if chosen_index < len(self.choices):
                self.choose(chosen_index)
                return True

        if key in ("e", "enter", "space") and self.choices:
            self.choose(self.selected_choice_index)
            return True

        if key == "left mouse down":
            hovered = mouse.hovered_entity
            if hovered in self.choice_entries and hovered.enabled:
                self.choose(hovered.choice_index)
                return True

        return False


class PauseMenu:
    def __init__(self):
        self.is_open = False
        self.selected_index = 0
        self.buttons = []

        self.root = make_ui_root(enabled=False)
        self.backdrop = Entity(
            parent=self.root,
            model="quad",
            scale=(2, 1.2),
            color=C(2, 4, 9, 188),
        )
        self.panel = Entity(
            parent=self.root,
            model="quad",
            scale=(0.70, 0.62),
            color=C(10, 18, 34, 244),
            texture=console_panel_texture,
        )
        style_panel(self.panel, C(10, 18, 34, 244))
        self.panel_edge = Entity(
            parent=self.root,
            model="quad",
            position=(0, 0.285),
            scale=(0.70, 0.004),
            color=C(102, 168, 225, 140),
        )
        self.panel_icon = Entity(
            parent=self.root,
            model="quad",
            position=(-0.31, 0.22, -0.01),
            scale=(0.06, 0.06),
            texture=ui_icon_circle_texture or ui_icon_square_texture,
            color=C(138, 214, 255, 150),
        )
        self.title = Text(
            parent=self.root,
            text="ПАУЗА",
            position=(0, 0.220),
            origin=(0, 0),
            scale=0.92,
            color=C(168, 220, 255),
            font=TITLE_FONT,
        )
        self.subtitle = Text(
            parent=self.root,
            text="Esc: продолжить. 1-6: выбор.",
            position=(0, 0.160),
            origin=(0, 0),
            scale=0.46,
            color=C(204, 220, 242, 210),
            font=BODY_FONT,
        )
        self.subtitle.text = "Esc: продолжить. 1-6: выбор."

        button_specs = (
            "1. Продолжить",
            "2. Выйти из игры",
        )

        for index, label in enumerate(button_specs):
            button = build_standard_ui_button(
                parent=self.root,
                label=label,
                position=(0, 0.080 - index * 0.064),
                scale=(0.54, 0.052),
                button_index=index,
                text_size=0.36,
            )
            self.buttons.append(button)
        for index in range(len(self.buttons), 6):
            button = build_standard_ui_button(
                parent=self.root,
                label="",
                position=(0, 0.080 - index * 0.064),
                scale=(0.54, 0.052),
                button_index=index,
                text_size=0.36,
            )
            self.buttons.append(button)
        self.status_text = Text(
            parent=self.root,
            text="",
            position=(0, -0.295),
            origin=(0, 0),
            scale=0.42,
            color=C(140, 220, 255, 210),
            font=BODY_FONT,
        )
        self._apply_layout()
        self._refresh_labels()
        register_ui_layout(self._apply_layout)

    def _apply_layout(self):
        safe_left, safe_right, safe_top, safe_bottom = ui_scale_manager.safe_rect()
        safe_width = safe_right - safe_left
        safe_height = safe_top - safe_bottom

        panel_width = ui_scale_manager.panel_width(0.68, 0.56, 0.78)
        panel_height = clamp(safe_height * 0.78, 0.56, 0.72)
        panel_center_y = (safe_top + safe_bottom) * 0.12

        self.backdrop.position = ((safe_left + safe_right) * 0.5, (safe_top + safe_bottom) * 0.5)
        self.backdrop.scale = (safe_width + 0.20, safe_height + 0.16)
        self.panel.position = (0, panel_center_y)
        self.panel.scale = (panel_width, panel_height)
        self.panel_edge.scale = (panel_width, 0.004)
        self.panel_edge.position = (0, panel_center_y + panel_height * 0.46)
        self.panel_icon.position = (-panel_width * 0.42, panel_center_y + panel_height * 0.35, -0.01)
        self.panel_icon.scale = (0.06, 0.06)
        self.title.position = (0, panel_center_y + panel_height * 0.34)
        self.subtitle.position = (0, panel_center_y + panel_height * 0.24)
        self.status_text.position = (0, panel_center_y - panel_height * 0.46)
        apply_text_role(self.title, "title", multiplier=0.98)
        apply_text_role(self.subtitle, "meta", multiplier=1.05)
        apply_text_role(self.status_text, "meta", multiplier=0.98)

        button_width = panel_width - 0.14
        button_height = clamp(0.050 - ui_scale_manager.narrow_factor * 0.006, 0.043, 0.052)
        button_step = clamp(button_height + 0.012, 0.056, 0.066)
        first_button_y = panel_center_y + panel_height * 0.08
        for index, button in enumerate(self.buttons):
            button.scale = (button_width, button_height)
            button.position = (0, first_button_y - index * button_step)
            refresh_standard_ui_button_text(button)

    def open(self):
        if self.is_open or map_open_queued or galaxy_map.is_open or dialogue_ui.is_open:
            return

        self.is_open = True
        self.selected_index = 0
        self.status_text.text = ""
        self._apply_layout()
        self.root.enabled = True
        interaction_text.enabled = False
        interaction_panel.enabled = False
        set_controls_hint_state(False)
        set_text_block_state(map_message_text, map_message_panel, False)
        freeze_first_person()
        default_crosshair.enabled = False
        npc_crosshair.enabled = False
        self._refresh_buttons()

    def close(self):
        if not self.is_open:
            return

        self.is_open = False
        self.root.enabled = False
        restore_first_person()
        set_controls_hint_state(True)
        default_crosshair.enabled = True
        npc_crosshair.enabled = False

    def _refresh_labels(self):
        labels = (
            "1. Продолжить",
            f"2. Режим окна: {WINDOW_MODE_LABELS[display_settings['window_mode']]}",
            f"3. Монитор: {monitor_short_label(display_settings['monitor_index'])}",
            f"4. Размер окна: {window_profile_label()}",
            "5. Применить настройки окна",
            "6. Выйти из игры",
        )
        for button, label in zip(self.buttons, labels):
            button.text = label
            if button.text_entity:
                button.text_entity.text = label

    def _refresh_buttons(self):
        self._refresh_labels()
        hovered = mouse.hovered_entity if self.is_open and mouse.visible else None
        for index, button in enumerate(self.buttons):
            if hovered == button:
                set_standard_ui_button_state(button, "hot")
            elif index == self.selected_index:
                set_standard_ui_button_state(button, "selected")
            else:
                set_standard_ui_button_state(button, "base")

    def update(self):
        if not self.is_open:
            return

        hovered = mouse.hovered_entity
        if hovered in self.buttons:
            self.selected_index = hovered.button_index
        self._refresh_buttons()

    def activate_selected(self):
        if self.selected_index == 0:
            self.close()
            return

        if self.selected_index == 1:
            current_index = WINDOW_MODE_ORDER.index(display_settings["window_mode"])
            display_settings["window_mode"] = WINDOW_MODE_ORDER[(current_index + 1) % len(WINDOW_MODE_ORDER)]
            self.status_text.text = "Режим окна изменён. Нажми «Применить»."
            self._refresh_buttons()
            return

        if self.selected_index == 2:
            display_settings["monitor_index"] = (display_settings["monitor_index"] + 1) % max(1, len(DISPLAY_MONITORS))
            self.status_text.text = "Монитор изменён. Нажми «Применить»."
            self._refresh_buttons()
            return

        if self.selected_index == 3:
            current_index = int(clamp(display_settings["window_scale_index"], 0, len(WINDOWED_SCALE_PRESETS) - 1))
            display_settings["window_scale_index"] = (current_index + 1) % len(WINDOWED_SCALE_PRESETS)
            monitor_index = int(clamp(display_settings["monitor_index"], 0, max(0, len(DISPLAY_MONITORS) - 1)))
            monitor = DISPLAY_MONITORS[monitor_index]
            _x, _y, width, height = resolve_display_geometry(
                monitor,
                display_settings["window_mode"],
                display_settings["window_scale_index"],
            )
            self.status_text.text = f"Профиль окна: {window_profile_label()} ({width}x{height}). Нажми «Применить»."
            self._refresh_buttons()
            return

        if self.selected_index == 4:
            apply_display_settings()
            self.status_text.text = "Настройки окна применены."
            self._refresh_buttons()
            return

        quit_game()

    def input(self, key):
        if not self.is_open:
            return False

        if key == "escape":
            self.close()
            return True

        if key in ("up arrow", "w"):
            self.selected_index = max(0, self.selected_index - 1)
            self._refresh_buttons()
            return True

        if key in ("down arrow", "s"):
            self.selected_index = min(len(self.buttons) - 1, self.selected_index + 1)
            self._refresh_buttons()
            return True

        if key.isdigit():
            chosen_index = int(key) - 1
            if 0 <= chosen_index < len(self.buttons):
                self.selected_index = chosen_index
                self.activate_selected()
                return True

        if key in ("enter", "space"):
            self.activate_selected()
            return True

        if key == "left mouse down":
            hovered = mouse.hovered_entity
            if hovered in self.buttons:
                self.selected_index = hovered.button_index
                self.activate_selected()
                return True

        return True


class GalaxyMapUI:
    def __init__(self):
        self.is_open = False
        self.view_mode = "galaxy"
        self.zoom = 1.0
        self.min_zoom = 0.85
        self.max_zoom = 2.35
        self.pan_limit_x = 0.72
        self.pan_limit_y = 0.44
        self.pulse_time = 0.0
        self.current_system_name = "Станция Валькир"
        self.selected_system_name = self.current_system_name
        self.hovered_system_name = None
        self.map_spec = STAR_MAP_SPEC
        self.render_layers = self.map_spec.get("recommended_approach", {}).get(
            "render_layers",
            [
                "nebula_background",
                "starfield_points",
                "cluster_labels",
                "travel_routes",
                "system_focus_panel",
                "hover_and_selection_fx",
            ],
        )
        self.system_lookup = {entry["name"]: entry for entry in GALAXY_SYSTEMS}
        self.ed3d_galaxy_data = self._build_ed3d_galaxy_data()
        self.display_positions = self._build_display_positions()
        self.route_graph = self._build_route_graph()
        self.system_buttons = {}
        self.node_glows = []
        self.active_sector_name = self.current_system_name
        self.current_local_by_sector = {}
        self.selected_local_name = None
        self.hovered_local_name = None
        self.local_buttons = {}
        self.local_lookup = {}
        self.local_route_graph = {}
        self.local_glows = []
        self.local_route_preview = None

        self.root = make_ui_root(enabled=False)
        self.backdrop = Entity(
            parent=self.root,
            model="quad",
            scale=(2.05, 1.22),
            color=C(1, 3, 10, 248),
            texture=console_screen_texture or console_panel_texture,
        )
        self.backdrop_nebula = Entity(
            parent=self.root,
            model="quad",
            position=(-0.08, -0.02),
            scale=(1.80, 1.00),
            color=C(13, 35, 86, 72),
            texture=radial_gradient_texture or console_panel_texture,
        )

        self.header = Text(
            parent=self.root,
            text="ЗВЁЗДНАЯ КАРТА",
            position=(-0.67, 0.43),
            scale=0.98,
            color=C(166, 220, 255, 255),
            font=TITLE_FONT,
        )
        apply_text_role(self.header, "title", multiplier=1.00, color_value=C(166, 220, 255, 255), font_value=TITLE_FONT)
        self.subheader = Text(
            parent=self.root,
            text="Голографическая навигация сектора  |  ПКМ панорама  |  Колесо масштаб  |  Enter проложить курс",
            position=(-0.67, 0.37),
            scale=0.50,
            color=C(154, 182, 216, 198),
            font=BODY_FONT,
        )
        apply_text_role(self.subheader, "meta", multiplier=1.04, color_value=C(154, 182, 216, 198), font_value=BODY_FONT)
        self.header_accent = Entity(
            parent=self.root,
            model="quad",
            position=(-0.12, 0.395),
            scale=(0.96, 0.003),
            color=C(78, 150, 228, 118),
        )
        self.back_button = build_standard_ui_button(
            parent=self.root,
            label="Назад к галактике",
            position=(0.52, -0.338),
            scale=(0.34, 0.054),
            button_index=0,
            on_click=self.show_galaxy_view,
            text_size=0.36,
        )
        self.back_button.z = -0.060
        self.back_button.enabled = False

        self.viewport_shell = Entity(
            parent=self.root,
            model="quad",
            position=(-0.17, -0.01),
            scale=(1.14, 0.78),
            color=C(5, 12, 28, 228),
            texture=console_panel_texture or ui_button_base_texture,
        )
        self.viewport_glow = Entity(
            parent=self.root,
            model="quad",
            position=(-0.17, -0.01),
            scale=(1.24, 0.84),
            color=C(18, 58, 126, 46),
            texture=radial_gradient_texture or console_panel_texture,
        )
        self.viewport = Entity(
            parent=self.root,
            model="quad",
            position=(-0.19, -0.01),
            scale=(1.04, 0.68),
            color=C(1, 7, 20, 92),
            texture=console_panel_texture or ui_button_base_texture,
        )
        self.viewport_border_top = Entity(parent=self.root, model="quad", position=(-0.19, 0.332), scale=(1.08, 0.004), color=C(92, 168, 240, 132))
        self.viewport_border_bottom = Entity(parent=self.root, model="quad", position=(-0.19, -0.350), scale=(1.08, 0.003), color=C(92, 168, 240, 56))
        self.viewport_border_left = Entity(parent=self.root, model="quad", position=(-0.728, -0.01), scale=(0.004, 0.69), color=C(92, 168, 240, 94))
        self.viewport_border_right = Entity(parent=self.root, model="quad", position=(0.348, -0.01), scale=(0.003, 0.69), color=C(92, 168, 240, 74))

        self.map_content = Entity(parent=self.viewport, position=(0.0, -0.01), scale=0.92, z=-0.02)
        self.map_base_scale = 0.92
        self.map_base_y = -0.01
        self.galaxy_layer = Entity(parent=self.map_content)
        self.local_layer = Entity(parent=self.map_content, enabled=False)
        self.galaxy_background = Entity(
            parent=self.galaxy_layer,
            model="quad",
            position=(0.02, 0.01),
            rotation_z=0,
            scale=(0.001, 0.001),
            z=-0.080,
            color=C(2, 8, 22, 0),
            enabled=False,
        )
        self.galaxy_background_glow = Entity(
            parent=self.galaxy_layer,
            model="quad",
            scale=(0.001, 0.001),
            z=-0.081,
            color=C(7, 24, 64, 0),
            enabled=False,
        )
        self.starfield_parent = Entity(parent=self.galaxy_layer)
        self.routes_parent = Entity(parent=self.galaxy_layer)
        self.system_parent = Entity(parent=self.galaxy_layer)
        self.cluster_parent = Entity(parent=self.galaxy_layer)
        self.sector_fog_parent = Entity(parent=self.galaxy_layer)
        self.galaxy_disk = Entity(
            parent=self.galaxy_layer,
            model="quad",
            scale=(0.001, 0.001),
            z=-0.032,
            color=C(22, 64, 135, 0),
            enabled=False,
        )
        self.holo_core = Entity(
            parent=self.galaxy_layer,
            model="quad",
            scale=(0.001, 0.001),
            z=-0.031,
            color=C(10, 42, 110, 0),
            enabled=False,
        )
        self.inner_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=(0.42, 0.002, 0.002),
            z=-0.026,
            color=C(118, 196, 255, 22),
        )
        self.mid_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=(0.002, 0.42, 0.002),
            z=-0.026,
            color=C(92, 156, 235, 16),
        )
        self.outer_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=(0.74, 0.002, 0.002),
            z=-0.026,
            color=C(76, 132, 225, 12),
        )
        self.scan_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=(0.002, 0.58, 0.002),
            z=-0.027,
            color=C(70, 110, 195, 14),
        )
        self.axis_horizontal = Entity(
            parent=self.galaxy_layer,
            model="quad",
            position=(0, 0, -0.028),
            scale=(0.94, 0.002),
            color=C(92, 144, 215, 32),
        )
        self.axis_vertical = Entity(
            parent=self.galaxy_layer,
            model="quad",
            position=(0, 0, -0.028),
            scale=(0.002, 0.76),
            color=C(92, 144, 215, 24),
        )

        self.selection_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=0.10,
            z=-0.04,
            color=C(130, 220, 255, 188),
            enabled=False,
        )
        self.selection_marker = Entity(parent=self.galaxy_layer, z=-0.046)
        for angle in (0, 90, 180, 270):
            Entity(
                parent=self.selection_marker,
                model="cube",
                position=(cos(angle * 3.14159265 / 180) * 0.70, sin(angle * 3.14159265 / 180) * 0.70, -0.006),
                rotation_z=angle,
                scale=(0.46, 0.042, 0.020),
                color=C(144, 232, 255, 190),
            )
            Entity(
                parent=self.selection_marker,
                model="cube",
                position=(cos(angle * 3.14159265 / 180) * 0.42, sin(angle * 3.14159265 / 180) * 0.42, -0.007),
                rotation_z=angle + 90,
                scale=(0.22, 0.030, 0.018),
                color=C(90, 180, 255, 112),
            )
        Entity(parent=self.selection_marker, model="sphere", scale=(1.45, 1.45, 0.12), color=C(80, 210, 255, 24))
        self.current_ring = Entity(
            parent=self.galaxy_layer,
            model="cube",
            scale=0.12,
            z=-0.045,
            color=C(255, 208, 120, 0),
            enabled=False,
        )
        self.current_ship_marker = Entity(parent=self.galaxy_layer, z=-0.050)
        Entity(parent=self.current_ship_marker, model="cube", position=(0.000, 0.000, -0.006), scale=(0.060, 0.016, 0.012), color=C(255, 214, 120, 232))
        Entity(parent=self.current_ship_marker, model="cube", position=(0.032, 0.000, -0.007), scale=(0.024, 0.010, 0.010), color=C(255, 244, 190, 238))
        Entity(parent=self.current_ship_marker, model="cube", position=(-0.012, 0.024, -0.008), rotation_z=-18, scale=(0.042, 0.010, 0.010), color=C(126, 212, 255, 190))
        Entity(parent=self.current_ship_marker, model="cube", position=(-0.012, -0.024, -0.008), rotation_z=18, scale=(0.042, 0.010, 0.010), color=C(126, 212, 255, 190))
        Entity(parent=self.current_ship_marker, model="sphere", position=(-0.040, 0.000, -0.010), scale=(0.014, 0.014, 0.010), color=C(110, 226, 255, 180))

        self.local_backdrop = Entity(
            parent=self.local_layer,
            model="quad",
            scale=(1.04, 0.68),
            z=-0.080,
            color=C(3, 9, 22, 42),
        )
        self.local_system_plane = Entity(
            parent=self.local_layer,
            model="quad",
            scale=(0.88, 0.60),
            z=-0.078,
            color=C(35, 86, 190, 0),
            enabled=False,
        )
        self.local_scan_line = Entity(
            parent=self.local_layer,
            model="quad",
            position=(0.0, -0.30, -0.068),
            scale=(1.00, 0.002),
            color=C(138, 230, 255, 70),
        )
        self.local_glow = Entity(
            parent=self.local_layer,
            model="quad",
            scale=(0.92, 0.62),
            z=-0.079,
            color=C(60, 118, 240, 0),
            enabled=False,
        )
        self.local_starfield_parent = Entity(parent=self.local_layer)
        self.local_fog_parent = Entity(parent=self.local_layer)
        self.local_orbits_parent = Entity(parent=self.local_layer)
        self.local_routes_parent = Entity(parent=self.local_layer)
        self.local_nodes_parent = Entity(parent=self.local_layer)
        self.local_labels_parent = Entity(parent=self.local_layer)
        self.local_selection_ring = Entity(
            parent=self.local_layer,
            model="cube",
            scale=0.09,
            z=-0.076,
            color=C(130, 220, 255, 0),
            enabled=False,
        )
        self.local_selection_marker = Entity(parent=self.local_layer, z=-0.074)
        for angle in (0, 90, 180, 270):
            Entity(
                parent=self.local_selection_marker,
                model="cube",
                position=(cos(angle * 3.14159265 / 180) * 0.68, sin(angle * 3.14159265 / 180) * 0.68, -0.006),
                rotation_z=angle,
                scale=(0.42, 0.040, 0.018),
                color=C(144, 232, 255, 184),
            )
            Entity(
                parent=self.local_selection_marker,
                model="cube",
                position=(cos(angle * 3.14159265 / 180) * 0.39, sin(angle * 3.14159265 / 180) * 0.39, -0.007),
                rotation_z=angle + 90,
                scale=(0.18, 0.028, 0.016),
                color=C(90, 180, 255, 104),
            )
        Entity(parent=self.local_selection_marker, model="sphere", scale=(1.35, 1.35, 0.10), color=C(80, 210, 255, 22))
        self.local_current_ring = Entity(
            parent=self.local_layer,
            model="cube",
            scale=0.12,
            z=-0.078,
            color=C(255, 208, 120, 0),
            enabled=False,
        )
        self.local_current_marker = Entity(parent=self.local_layer, z=-0.075)
        Entity(parent=self.local_current_marker, model="sphere", scale=(1.45, 1.45, 0.10), color=C(255, 208, 120, 28))
        for angle in (35, 145, 215, 325):
            Entity(
                parent=self.local_current_marker,
                model="cube",
                position=(cos(angle * 3.14159265 / 180) * 0.52, sin(angle * 3.14159265 / 180) * 0.52, -0.006),
                rotation_z=angle,
                scale=(0.30, 0.034, 0.018),
                color=C(255, 214, 120, 160),
            )
        self.route_preview = None
        build_steps = {
            "nebula_background": self._build_nebulae,
            "starfield_points": self._build_background_starfield,
            "cluster_labels": self._build_cluster_labels,
            "travel_routes": self._build_routes,
            "hover_and_selection_fx": self._build_systems,
        }
        for layer_name in self.render_layers:
            build_step = build_steps.get(layer_name)
            if build_step:
                build_step()

        self.info_panel = Entity(
            parent=self.root,
            model="quad",
            position=(0.52, -0.01),
            scale=(0.50, 0.76),
            color=C(5, 11, 26, 238),
            texture=console_panel_texture or ui_button_base_texture,
        )
        self.info_panel_glow = Entity(
            parent=self.root,
            model="quad",
            position=(0.52, -0.01),
            scale=(0.54, 0.80),
            color=C(13, 45, 98, 54),
            texture=radial_gradient_texture or console_panel_texture,
        )
        self.info_panel_edge = Entity(parent=self.root, model="quad", position=(0.52, 0.355), scale=(0.50, 0.004), color=C(106, 176, 240, 138))
        self.info_icon = Entity(
            parent=self.info_panel,
            model="quad",
            position=(-0.20, 0.318, -0.01),
            scale=(0.075, 0.075),
            texture=ui_icon_circle_texture or ui_icon_square_texture,
            color=C(142, 220, 255, 168),
        )

        self.system_name_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, 0.292),
            scale=0.82,
            color=C(226, 241, 255, 255),
            font=TITLE_FONT,
        )
        apply_text_role(self.system_name_text, "subtitle", multiplier=1.14, color_value=C(226, 241, 255, 255), font_value=TITLE_FONT)
        self.region_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, 0.208),
            scale=0.58,
            color=C(136, 202, 255, 215),
            font=BODY_FONT,
        )
        apply_text_role(self.region_text, "body", multiplier=1.00, color_value=C(136, 202, 255, 215), font_value=BODY_FONT)
        self.threat_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, 0.135),
            scale=0.56,
            color=C(255, 186, 144, 220),
            font=BODY_FONT,
        )
        apply_text_role(self.threat_text, "body", multiplier=0.98, color_value=C(255, 186, 144, 220), font_value=BODY_FONT)
        self.summary_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, 0.015),
            scale=0.54,
            color=C(208, 220, 240, 214),
            font=BODY_FONT,
            line_height=1.15,
        )
        apply_text_role(self.summary_text, "body", multiplier=0.96, color_value=C(208, 220, 240, 214), font_value=BODY_FONT, line_height=1.15)
        self.location_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, -0.172),
            scale=0.55,
            color=C(255, 212, 132, 220),
            font=BODY_FONT,
        )
        apply_text_role(self.location_text, "body", multiplier=0.97, color_value=C(255, 212, 132, 220), font_value=BODY_FONT)
        self.route_text = Text(
            parent=self.info_panel,
            text="",
            position=(-0.21, -0.248),
            scale=0.52,
            color=C(144, 228, 255, 220),
            font=BODY_FONT,
            line_height=1.1,
        )
        apply_text_role(self.route_text, "meta", multiplier=1.05, color_value=C(144, 228, 255, 220), font_value=BODY_FONT, line_height=1.1)
        self.footer_text = Text(
            parent=self.root,
            text="",
            position=(-0.67, -0.43),
            scale=0.46,
            color=C(148, 170, 208, 168),
            font=TECH_FONT,
        )
        apply_text_role(self.footer_text, "meta", multiplier=0.98, color_value=C(148, 170, 208, 168), font_value=TECH_FONT)
        self.footer_text.enabled = False
        self.info_wrap = 30

        register_ui_layout(self._apply_layout)
        self._apply_layout()
        self.select_system(self.current_system_name, initial=True)

    def _apply_layout(self):
        safe_left, safe_right, safe_top, safe_bottom = ui_scale_manager.safe_rect()
        safe_width = safe_right - safe_left
        safe_height = safe_top - safe_bottom
        safe_center_x = (safe_left + safe_right) * 0.5
        safe_center_y = (safe_top + safe_bottom) * 0.5

        info_width = ui_scale_manager.panel_width(0.46, 0.34, 0.52)
        gutter = 0.030
        map_left = safe_left + 0.010
        map_right = safe_right - info_width - gutter
        if map_right - map_left < 0.62:
            info_width = clamp(info_width - (0.62 - (map_right - map_left)), 0.32, 0.46)
            map_right = safe_right - info_width - gutter

        viewport_width = clamp(map_right - map_left, 0.62, 1.16)
        viewport_height = clamp(safe_height - 0.19, 0.58, 0.80)
        viewport_center_x = map_left + viewport_width * 0.5
        viewport_center_y = safe_center_y - 0.02
        info_height = clamp(viewport_height + 0.08, 0.66, 0.84)
        info_center_x = map_right + gutter + info_width * 0.5

        self.backdrop.position = (safe_center_x, safe_center_y)
        self.backdrop.scale = (safe_width + 0.18, safe_height + 0.14)
        self.backdrop_nebula.position = (viewport_center_x - viewport_width * 0.09, viewport_center_y)
        self.backdrop_nebula.scale = (viewport_width * 1.08, viewport_height * 1.26)

        self.header.position = (safe_left, safe_top - 0.04)
        self.subheader.position = (safe_left, safe_top - 0.09)
        apply_text_role(self.header, "title", multiplier=1.00)
        apply_text_role(self.subheader, "meta", multiplier=1.04)
        self.header_accent.position = (viewport_center_x, safe_top - 0.07)
        self.header_accent.scale = (viewport_width, 0.003)

        self.viewport_shell.position = (viewport_center_x, viewport_center_y)
        self.viewport_shell.scale = (viewport_width + 0.10, viewport_height + 0.10)
        self.viewport_glow.position = (viewport_center_x, viewport_center_y)
        self.viewport_glow.scale = (viewport_width + 0.18, viewport_height + 0.16)
        self.viewport.position = (viewport_center_x, viewport_center_y)
        self.viewport.scale = (viewport_width, viewport_height)
        self.viewport_border_top.position = (viewport_center_x, viewport_center_y + viewport_height * 0.50)
        self.viewport_border_top.scale = (viewport_width + 0.04, 0.004)
        self.viewport_border_bottom.position = (viewport_center_x, viewport_center_y - viewport_height * 0.50)
        self.viewport_border_bottom.scale = (viewport_width + 0.04, 0.003)
        self.viewport_border_left.position = (viewport_center_x - viewport_width * 0.50, viewport_center_y)
        self.viewport_border_left.scale = (0.004, viewport_height + 0.01)
        self.viewport_border_right.position = (viewport_center_x + viewport_width * 0.50, viewport_center_y)
        self.viewport_border_right.scale = (0.003, viewport_height + 0.01)

        self.info_panel.position = (info_center_x, viewport_center_y)
        self.info_panel.scale = (info_width, info_height)
        self.info_panel_glow.position = (info_center_x, viewport_center_y)
        self.info_panel_glow.scale = (info_width + 0.04, info_height + 0.04)
        self.info_panel_edge.position = (info_center_x, viewport_center_y + info_height * 0.50 - 0.01)
        self.info_panel_edge.scale = (info_width, 0.004)
        self.info_icon.position = (-0.20, 0.318, -0.01)
        self.info_icon.scale = (0.075, 0.075)

        self.back_button.position = (info_center_x, safe_bottom + 0.050)
        self.back_button.scale = (clamp(info_width - 0.13, 0.30, 0.40), 0.052)
        refresh_standard_ui_button_text(self.back_button)
        self.footer_text.position = (safe_left, safe_bottom + 0.01)
        apply_text_role(self.footer_text, "meta", multiplier=0.98)
        self.info_wrap = int(clamp(24 + info_width * 26, 24, 36))
        if hasattr(self.summary_text, "raw_text"):
            self.summary_text.wordwrap = self.info_wrap
        if hasattr(self.route_text, "raw_text"):
            self.route_text.wordwrap = self.info_wrap

        self.pan_limit_x = clamp(0.70 * (viewport_width / 1.04), 0.34, 0.80)
        self.pan_limit_y = clamp(0.44 * (viewport_height / 0.68), 0.24, 0.56)
        if self.is_open:
            self._clamp_pan()

    def _build_ed3d_galaxy_data(self):
        """ED3D is a JS/Three.js map; in Ursina we reuse its systems/routes/coords idea."""
        coords = {
            "Станция Валькир": (-430, -80, -130),
            "Врата Сигнуса": (-170, 110, 70),
            "Корона Эоса": (55, -55, -310),
            "Завеса Персея": (280, 180, 170),
            "Пояс Хепри": (360, -120, -90),
            "Бастион Никс": (520, 20, 20),
            "Разлом Орфея": (40, 260, 330),
            "Дредмайр": (-330, -250, -265),
        }
        systems = []
        for entry in GALAXY_SYSTEMS:
            x, y, z = coords.get(
                entry["name"],
                (entry["position"][0] * 820, 0, entry["position"][1] * 720),
            )
            systems.append(
                {
                    "name": entry["name"],
                    "coords": {"x": x, "y": y, "z": z},
                    "infos": {
                        "region": entry["region"],
                        "threat": entry["threat"],
                        "summary": entry["summary"],
                    },
                    "cat": ["sector"],
                }
            )

        return {
            "categories": {"sector": {"name": "Сектор", "color": "66d9ff"}},
            "systems": systems,
            "routes": [
                {"title": "Секторный коридор", "points": [{"s": start_name}, {"s": end_name}]}
                for start_name, end_name in GALAXY_ROUTES
            ],
        }

    def _build_display_positions(self):
        layout = {}
        for system in self.ed3d_galaxy_data["systems"]:
            coords = system["coords"]
            # ED3D stores x/y/z; the UI projects depth into x/y so sectors no longer sit on the old flat layout.
            layout[system["name"]] = (
                clamp(coords["x"] / 1040 + coords["y"] / 4200, -0.48, 0.48),
                clamp(coords["z"] / 900 - coords["y"] / 5200, -0.31, 0.32),
            )

        return layout

    def _map_position(self, system_name):
        return self.display_positions.get(system_name, self.system_lookup[system_name]["position"])

    def _map_depth(self, system_name):
        for system in self.ed3d_galaxy_data["systems"]:
            if system["name"] == system_name:
                return clamp(system["coords"]["y"] / 4200, -0.06, 0.06)
        return 0

    def _reset_pan(self):
        self.map_content.x = 0
        self.map_content.y = self.map_base_y

    def pan_map(self, delta_x, delta_y):
        self.map_content.x += delta_x / max(self.zoom, 0.01)
        self.map_content.y += delta_y / max(self.zoom, 0.01)
        self._clamp_pan()

    def _clear_children(self, parent):
        for child in list(parent.children):
            destroy(child)
        try:
            for child_node in parent.getChildren():
                child_node.removeNode()
        except Exception:
            pass

    def _color_from_tint(self, tint, alpha):
        return C(*tint.rgba32[:3], alpha)

    def _make_depth_shadow(self, parent, position, tint, width, height, z=-0.066, rotation=0):
        return Entity(
            parent=parent,
            model="sphere",
            position=(position[0], position[1] - 0.014, z),
            rotation_z=rotation,
            scale=(width, height, 0.004),
            color=self._color_from_tint(tint, 16),
        )

    def _decorate_sector_node(self, node, entry, index, depth):
        tint = entry["tint"]
        Entity(
            parent=node,
            model="sphere",
            scale=(2.75, 2.75, 0.34),
            color=self._color_from_tint(tint, 30),
        )
        Entity(
            parent=node,
            model="sphere",
            scale=(1.36, 1.36, 0.34),
            color=self._color_from_tint(tint, 84),
        )
        Entity(
            parent=node,
            model="sphere",
            position=(0.15, 0.16, -0.006),
            scale=0.30,
            color=C(248, 252, 255, 185),
        )

        for ring_index, rotation in enumerate((index * 19, index * 19 + 62, index * 19 + 121)):
            Entity(
                parent=node,
                model="cube",
                rotation_z=rotation,
                scale=(3.10 - ring_index * 0.40, 0.034, 0.020),
                color=self._color_from_tint(tint, 68 - ring_index * 14),
            )

        for pip_index, side in enumerate((-1, 1)):
            Entity(
                parent=node,
                model="cube",
                position=(side * (1.62 + pip_index * 0.16), 0.0, -0.010),
                rotation_z=index * 13,
                scale=(0.24, 0.24, 0.14),
                color=self._color_from_tint(tint, 112),
            )

        node.z = -0.035 + depth

    def _decorate_local_node(self, button, node, index):
        tint = node["tint"]
        node_type = node["type"]
        position = node["position"]
        ring_scale = node["ring_scale"]

        self._make_depth_shadow(
            self.local_nodes_parent,
            position,
            tint,
            width=ring_scale * (3.4 if node_type == "star" else 2.0),
            height=ring_scale * (1.05 if node_type == "star" else 0.62),
            z=-0.074,
            rotation=index * 0.25,
        )

        if node_type == "star":
            for scale_value, alpha in ((3.8, 26), (2.3, 52), (1.25, 122)):
                Entity(parent=button, model="sphere", scale=scale_value, color=self._color_from_tint(tint, alpha))
            for rotation in (0, 45, 90, 135):
                Entity(
                    parent=button,
                    model="cube",
                    rotation_z=rotation,
                    scale=(3.3, 0.028, 0.018),
                    color=self._color_from_tint(tint, 72),
                )
            make_holo_ellipse(self.local_nodes_parent, position, ring_scale * 2.25, ring_scale * 1.00, self._color_from_tint(tint, 98), 0.0018, -0.064, 20, rotation=0.55)
            return

        if node_type == "planet":
            Entity(parent=button, model="sphere", scale=(1.75, 1.75, 0.42), color=self._color_from_tint(tint, 42))
            Entity(parent=button, model="sphere", scale=(1.08, 1.08, 0.40), color=self._color_from_tint(tint, 180))
            Entity(
                parent=button,
                model="cube",
                rotation_z=22 + index * 8,
                scale=(2.80, 0.042, 0.018),
                color=C(218, 242, 255, 70),
            )
            Entity(
                parent=button,
                model="sphere",
                position=(-0.20, 0.18, -0.010),
                scale=0.28,
                color=C(250, 252, 255, 130),
            )
            make_holo_ellipse(self.local_nodes_parent, position, ring_scale * 1.75, ring_scale * 0.70, self._color_from_tint(tint, 72), 0.0016, -0.066, 16, rotation=0.36)
            return

        if node_type == "station":
            button.model = "cube"
            button.scale = node["scale"]
            button.color = self._color_from_tint(tint, 0)
            button.highlight_color = self._color_from_tint(tint, 18)
            button.pressed_color = self._color_from_tint(tint, 30)
            Entity(parent=button, model="cube", position=(0, 0, -0.010), scale=(0.56, 0.88, 0.18), color=C(226, 244, 255, 190))
            Entity(parent=button, model="cube", position=(-0.44, 0, -0.012), scale=(0.32, 0.54, 0.14), color=self._color_from_tint(tint, 150))
            Entity(parent=button, model="cube", position=(0.44, 0, -0.012), scale=(0.32, 0.54, 0.14), color=self._color_from_tint(tint, 150))
            Entity(parent=button, model="cube", position=(0, 0.42, -0.014), scale=(1.00, 0.12, 0.14), color=C(132, 216, 255, 118))
            Entity(parent=button, model="cube", position=(0, -0.42, -0.014), scale=(1.00, 0.12, 0.14), color=C(132, 216, 255, 92))
            Entity(parent=button, model="sphere", scale=(1.34, 1.02, 0.16), color=self._color_from_tint(tint, 18))
            make_holo_ellipse(self.local_nodes_parent, position, ring_scale * 1.35, ring_scale * 0.56, self._color_from_tint(tint, 70), 0.0016, -0.066, 18, rotation=-0.28)
            return

        if node_type == "railgun":
            button.model = "cube"
            button.scale = node["scale"]
            button.color = self._color_from_tint(tint, 0)
            button.highlight_color = self._color_from_tint(tint, 18)
            button.pressed_color = self._color_from_tint(tint, 30)
            Entity(parent=button, model="cube", position=(0, 0.24, -0.010), scale=(1.18, 0.10, 0.14), color=C(208, 242, 255, 150))
            Entity(parent=button, model="cube", position=(0, -0.24, -0.010), scale=(1.18, 0.10, 0.14), color=C(208, 242, 255, 126))
            Entity(parent=button, model="cube", position=(-0.48, 0, -0.012), scale=(0.12, 0.64, 0.13), color=self._color_from_tint(tint, 118))
            Entity(parent=button, model="cube", position=(0.48, 0, -0.012), scale=(0.12, 0.64, 0.13), color=self._color_from_tint(tint, 118))
            Entity(parent=button, model="cube", position=(0.56, 0, -0.014), scale=(0.18, 0.42, 0.12), color=C(155, 230, 255, 134))
            Entity(parent=button, model="sphere", position=(-0.58, 0, -0.016), scale=(0.25, 0.25, 0.12), color=C(155, 230, 255, 92))
            Entity(parent=button, model="sphere", scale=(1.35, 0.84, 0.12), color=self._color_from_tint(tint, 18))
            make_holo_ellipse(self.local_nodes_parent, position, ring_scale * 1.28, ring_scale * 0.72, self._color_from_tint(tint, 78), 0.0016, -0.066, 18, rotation=0.0)
            return

    def _set_header_for_galaxy(self):
        self.header.text = "КАРТА ГАЛАКТИКИ"
        self.subheader.text = "ЛКМ выбрать сектор  |  Enter проложить курс  |  ПКМ панорама  |  Колесо масштаб"
        self.footer_text.text = ""
        self.footer_text.enabled = False
        self.back_button.enabled = False

    def _set_header_for_sector(self, sector_name):
        self.header.text = f"СЕКТОР: {sector_name.upper()}"
        self.subheader.text = "ЛКМ выбрать узел  |  Enter перейти по маршруту  |  Esc назад к галактике"
        self.footer_text.text = ""
        self.footer_text.enabled = False
        self.back_button.enabled = True

    def _update_galaxy_panel(self, sector_name):
        sector = self.system_lookup[sector_name]
        self.system_name_text.text = sector["name"]
        self.region_text.text = f"Сектор: {sector['region']}"
        self.threat_text.text = f"Угроза: {THREAT_LABELS.get(sector['threat'], sector['threat'])}"
        set_wrapped_text(self.summary_text, sector["summary"], self.info_wrap)
        self.location_text.text = f"Текущий сектор: {self.current_system_name}"
        set_wrapped_text(self.route_text, self._route_status(), self.info_wrap)

    def _build_sector_dataset(self, sector_name):
        sector = self.system_lookup[sector_name]
        sector_index = next((index for index, entry in enumerate(GALAXY_SYSTEMS) if entry["name"] == sector_name), 0)
        rng = random.Random(700 + sector_index * 19)
        accent = sector["tint"]
        star_name = f"Звезда сектора {sector_name}"
        station_name = f"Станция узла «{sector_name}»"
        rail_a_name = "\u0420\u0435\u043b\u044c\u0441\u043e\u0442\u0440\u043e\u043d \u0412\u043e\u0441\u0442\u043e\u043a"
        rail_b_name = "\u0420\u0435\u043b\u044c\u0441\u043e\u0442\u0440\u043e\u043d \u0422\u0435\u043d\u044c"
        node_specs = [
            {
                "name": star_name,
                "type": "star",
                "type_label": "Звезда",
                "position": (0.00, 0.00),
                "scale": 0.086,
                "ring_scale": 0.086,
                "tint": accent,
                "summary": f"Главная звезда сектора «{sector_name}». От её короны питаются локальные станции и рельсовые узлы.",
                "status": "Энергетическое ядро",
                "label_offset": (0.040, 0.022),
            },
            {
                "name": "Планета I",
                "type": "planet",
                "type_label": "Планета",
                "position": (0.17, 0.02),
                "scale": 0.040,
                "ring_scale": 0.040,
                "tint": C(110 + sector_index * 8, 176, 255),
                "summary": "Ближняя орбита. Используется для переработки топлива и ремонта малых корпусов.",
                "status": "Орбитальная промышленность",
                "label_offset": (0.036, -0.018),
            },
            {
                "name": "Планета II",
                "type": "planet",
                "type_label": "Планета",
                "position": (-0.24, -0.08),
                "scale": 0.046,
                "ring_scale": 0.046,
                "tint": C(255, 174 + sector_index * 4, 118),
                "summary": "Средняя орбита. Здесь держат склады, гарнизон и сигнальные ретрансляторы сектора.",
                "status": "Опорный мир",
                "label_offset": (0.040, 0.020),
            },
            {
                "name": "Планета III",
                "type": "planet",
                "type_label": "Планета",
                "position": (0.01, -0.27),
                "scale": 0.034,
                "ring_scale": 0.034,
                "tint": C(178, 132 + sector_index * 6, 255),
                "summary": "Внешняя орбита. Слабый трафик, тени сенсоров и редкие патрульные маршруты.",
                "status": "Внешний рубеж",
                "label_offset": (0.036, -0.020),
            },
            {
                "name": station_name,
                "type": "station",
                "type_label": "Станция",
                "position": (0.30, -0.14),
                "scale": (0.052, 0.044),
                "ring_scale": 0.052,
                "tint": C(110, 200, 255),
                "summary": "Орбитальная станция сектора. Здесь сходятся доки, переговорные каналы и полевые техбригады.",
                "status": "Точка швартовки",
                "label_offset": (0.042, 0.020),
            },
            {
                "name": rail_a_name,
                "type": "railgun",
                "type_label": "\u0420\u0435\u043b\u044c\u0441\u043e\u0442\u0440\u043e\u043d",
                "position": (-0.38, 0.20),
                "scale": (0.052, 0.052),
                "ring_scale": 0.052,
                "tint": C(124, 214, 255),
                "summary": "\u0420\u0430\u0437\u0433\u043e\u043d\u043d\u044b\u0439 \u0440\u0435\u043b\u044c\u0441\u043e\u0432\u044b\u0439 \u0443\u0437\u0435\u043b. \u041f\u0430\u0440\u043d\u044b\u0435 \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u044f\u044e\u0449\u0438\u0435 \u0432\u044b\u0432\u043e\u0434\u044f\u0442 \u043a\u043e\u0440\u0430\u0431\u043b\u044c \u043d\u0430 \u0431\u044b\u0441\u0442\u0440\u044b\u0439 \u043c\u0430\u0440\u0448\u0440\u0443\u0442 \u043f\u043e \u0441\u0435\u043a\u0442\u043e\u0440\u0443.",
                "status": "\u0423\u0437\u0435\u043b \u0440\u0430\u0437\u0433\u043e\u043d\u0430",
                "label_offset": (0.048, 0.020),
            },
            {
                "name": rail_b_name,
                "type": "railgun",
                "type_label": "\u0420\u0435\u043b\u044c\u0441\u043e\u0442\u0440\u043e\u043d",
                "position": (0.42, 0.24),
                "scale": (0.052, 0.052),
                "ring_scale": 0.052,
                "tint": C(96, 178, 255),
                "summary": "\u0414\u0430\u043b\u044c\u043d\u0438\u0439 \u0440\u0435\u043b\u044c\u0441\u043e\u0442\u0440\u043e\u043d \u0434\u043b\u044f \u0442\u0440\u0430\u0441\u0441 \u043a \u0432\u043d\u0435\u0448\u043d\u0438\u043c \u0440\u0443\u0431\u0435\u0436\u0430\u043c. \u0418\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440\u044b \u0434\u0435\u0440\u0436\u0430\u0442 \u043a\u043e\u0440\u0438\u0434\u043e\u0440 \u0433\u043e\u0442\u043e\u0432\u044b\u043c \u043a \u0441\u0442\u0430\u0440\u0442\u0443.",
                "status": "\u0414\u0430\u043b\u044c\u043d\u0438\u0439 \u0443\u0441\u043a\u043e\u0440\u0438\u0442\u0435\u043b\u044c",
                "label_offset": (0.048, -0.022),
            },
        ]

        orbit_radii = (0.17, 0.26, 0.35)
        orbit_angles = (12 + rng.uniform(-8, 10), -145 + rng.uniform(-10, 6), -88 + rng.uniform(-8, 10))
        for index, radius in enumerate(orbit_radii):
            node_specs[index + 1]["orbit_radius"] = radius
            node_specs[index + 1]["orbit_angle"] = orbit_angles[index]

        routes = [
            (star_name, "Планета I"),
            (star_name, "Планета II"),
            (star_name, "Планета III"),
            ("Планета I", station_name),
            ("Планета II", rail_a_name),
            (station_name, rail_b_name),
            ("Планета III", rail_b_name),
        ]

        return {
            "nodes": node_specs,
            "routes": routes,
            "current_default": station_name,
        }

    def _rebuild_sector_scene(self, sector_name):
        self._clear_children(self.local_starfield_parent)
        self._clear_children(self.local_fog_parent)
        self._clear_children(self.local_orbits_parent)
        self._clear_children(self.local_routes_parent)
        self._clear_children(self.local_nodes_parent)
        self._clear_children(self.local_labels_parent)
        self.local_buttons = {}
        self.local_lookup = {}
        self.local_route_graph = {}
        self.local_glows = []

        if self.local_route_preview:
            destroy(self.local_route_preview)
            self.local_route_preview = None

        sector = self.system_lookup[sector_name]
        dataset = self._build_sector_dataset(sector_name)
        rng = random.Random(910 + len(sector_name))

        self.local_glow.color = C(*sector["tint"].rgba32[:3], 28)
        self.local_backdrop.color = C(3, 9, 22, 42)
        self.local_system_plane.color = C(*sector["tint"].rgba32[:3], 12)
        self.local_glow.enabled = False
        self.local_system_plane.enabled = False

        for _ in range(72):
            Entity(
                parent=self.local_starfield_parent,
                model="sphere",
                position=(rng.uniform(-0.54, 0.54), rng.uniform(-0.33, 0.33), rng.uniform(-0.055, -0.010)),
                scale=rng.uniform(0.0012, 0.0048),
                color=C(rng.randint(120, 180), rng.randint(176, 228), 255, rng.randint(42, 116)),
            )

        for cloud_index in range(10):
            cloud_tint = sector["tint"] if cloud_index % 3 else C(80, 130, 220)
            Entity(
                parent=self.local_fog_parent,
                model="sphere",
                position=(
                    rng.uniform(-0.44, 0.44),
                    rng.uniform(-0.26, 0.26),
                    rng.uniform(-0.070, -0.044),
                ),
                rotation_z=rng.uniform(-35, 35),
                scale=(rng.uniform(0.045, 0.120), rng.uniform(0.010, 0.028), 0.004),
                color=C(*cloud_tint.rgba32[:3], rng.randint(5, 11)),
            )

        for radius in (0.18, 0.28, 0.38):
            orbit_points = (
                (radius, 0),
                (radius * 0.707, radius * 0.707),
                (0, radius),
                (-radius * 0.707, radius * 0.707),
                (-radius, 0),
                (-radius * 0.707, -radius * 0.707),
                (0, -radius),
                (radius * 0.707, -radius * 0.707),
            )
            for point_index, start in enumerate(orbit_points):
                end = orbit_points[(point_index + 1) % len(orbit_points)]
                make_route_line(
                    self.local_orbits_parent,
                    start,
                    end,
                    tint=C(84, 146, 226, 34),
                    thickness=0.0018,
                    z=-0.030,
                )

        Entity(
            parent=self.local_orbits_parent,
            model="sphere",
            scale=(0.28, 0.28),
            z=-0.050,
            color=C(*sector["tint"].rgba32[:3], 18),
        )

        node_positions = {}
        for node in dataset["nodes"]:
            node_positions[node["name"]] = node["position"]
            self.local_lookup[node["name"]] = node
            self.local_route_graph[node["name"]] = []

        for start_name, end_name in dataset["routes"]:
            start = node_positions[start_name]
            end = node_positions[end_name]
            route_distance = (Vec2(end[0], end[1]) - Vec2(start[0], start[1])).length()
            self.local_route_graph[start_name].append((end_name, route_distance))
            self.local_route_graph[end_name].append((start_name, route_distance))
            build_route_polyline(
                self.local_routes_parent,
                [Vec3(start[0], start[1], -0.024), Vec3(end[0], end[1], -0.024)],
                color_value=(0.24, 0.47, 0.74, 0.22),
                thickness=3.0,
                name="local_static_route_shadow",
            )
            build_route_polyline(
                self.local_routes_parent,
                [Vec3(start[0], start[1], -0.025), Vec3(end[0], end[1], -0.025)],
                color_value=(0.52, 0.86, 1.0, 0.50),
                thickness=1.4,
                name="local_static_route_core",
            )

        for index, node in enumerate(dataset["nodes"]):
            node_model = "sphere" if node["type"] in ("star", "planet") else "cube"
            node_scale = node["scale"]
            button = Button(
                parent=self.local_nodes_parent,
                model=node_model,
                position=(node["position"][0], node["position"][1], -0.060),
                scale=node_scale,
                color=node["tint"],
                highlight_scale=1.06,
                pressed_scale=0.96,
            )
            button.local_name = node["name"]
            button.ring_scale = node["ring_scale"]
            button.base_tint = node["tint"]
            button.on_click = Func(self.select_local_node, node["name"])
            self.local_buttons[node["name"]] = button

            self._decorate_local_node(button, node, index)

            glow = Entity(
                parent=button,
                model="sphere",
                scale=3.0 if node["type"] == "star" else 2.2,
                color=C(*node["tint"].rgba32[:3], 22 if node["type"] == "star" else 14),
            )
            glow.phase_offset = index * 0.8
            glow.base_scale = 2.6 if node["type"] == "star" else 2.0
            self.local_glows.append(glow)

            label = Text(
                parent=self.local_labels_parent,
                text=node["name"],
                position=(node["position"][0] + node["label_offset"][0], node["position"][1] + node["label_offset"][1], -0.070),
                scale=0.42 if node["type"] == "star" else 0.38,
                color=C(220, 238, 255, 232),
                font=TECH_FONT,
            )
            label.z = -0.070

        current_local = self.current_local_by_sector.get(sector_name, dataset["current_default"])
        if current_local not in self.local_lookup:
            current_local = dataset["current_default"]
        self.current_local_by_sector[sector_name] = current_local
        self.selected_local_name = current_local
        self.select_local_node(current_local, initial=True)

    def _update_local_panel(self, local_name):
        node = self.local_lookup[local_name]
        current_local = self.current_local_by_sector.get(self.active_sector_name, local_name)
        self.system_name_text.text = node["name"]
        self.region_text.text = f"Узел: {node['type_label']}"
        self.threat_text.text = f"Статус: {node['status']}"
        set_wrapped_text(self.summary_text, node["summary"], self.info_wrap)
        self.location_text.text = f"Текущий узел: {current_local}"
        if local_name == current_local:
            route_status = "Узел активен. Выбери другой объект, чтобы перестроить локальный маршрут."
        else:
            route_status = f"Выбран: {local_name}. Enter перестроит маршрут."
        set_wrapped_text(self.route_text, route_status, self.info_wrap)

    def _find_local_route_path(self, start_name, end_name):
        if start_name == end_name:
            return [start_name]

        open_paths = [(0, start_name, [start_name])]
        best_costs = {start_name: 0}
        while open_paths:
            open_paths.sort(key=lambda item: item[0])
            current_cost, current_name, path = open_paths.pop(0)
            if current_name == end_name:
                return path

            for next_name, edge_cost in self.local_route_graph.get(current_name, ()):
                next_cost = current_cost + edge_cost
                if next_cost >= best_costs.get(next_name, 999):
                    continue
                best_costs[next_name] = next_cost
                open_paths.append((next_cost, next_name, path + [next_name]))

        return [start_name, end_name]

    def _refresh_local_route_preview(self):
        if self.local_route_preview:
            destroy(self.local_route_preview)
            self.local_route_preview = None

        current_local = self.current_local_by_sector.get(self.active_sector_name)
        if not current_local or not self.selected_local_name or current_local == self.selected_local_name:
            return

        path = self._find_local_route_path(current_local, self.selected_local_name)
        self.local_route_preview = Entity(parent=self.local_layer)
        points = [Vec3(*self.local_lookup[node_name]["position"], -0.034) for node_name in path]
        build_route_polyline(
            self.local_route_preview,
            points,
            color_value=(0.28, 0.78, 1.0, 0.20),
            thickness=8.0,
            name="local_route_glow",
        )
        build_route_polyline(
            self.local_route_preview,
            points,
            color_value=(0.78, 0.94, 1.0, 0.92),
            thickness=3.0,
            name="local_route_core",
        )

        for node_name in path[1:-1]:
            point = self.local_lookup[node_name]["position"]
            Entity(
                parent=self.local_route_preview,
                model="sphere",
                position=(point[0], point[1], -0.035),
                scale=0.045,
                color=C(160, 230, 255, 128),
            )

        end = self.local_lookup[self.selected_local_name]["position"]
        Entity(
            parent=self.local_route_preview,
            model="sphere",
            position=(end[0], end[1], -0.035),
            scale=0.10,
            color=C(120, 224, 255, 44),
        )

    def show_galaxy_view(self, initial=False):
        self.view_mode = "galaxy"
        for child in self.map_content.children:
            child.enabled = child is not self.local_layer
        self.galaxy_layer.enabled = True
        self.local_layer.enabled = False
        self.active_sector_name = self.selected_system_name or self.current_system_name
        self.hovered_local_name = None
        self.set_zoom(1.0)
        self._reset_pan()
        self._set_header_for_galaxy()
        self.select_system(self.selected_system_name or self.current_system_name, initial=True if initial else False)

    def enter_sector(self, sector_name):
        self.active_sector_name = sector_name
        self.select_system(sector_name, initial=True)
        self.view_mode = "sector"
        for child in self.map_content.children:
            child.enabled = child is self.local_layer
        self.galaxy_layer.enabled = False
        self.local_layer.enabled = True
        self.hovered_system_name = None
        self.set_zoom(1.06)
        self._reset_pan()
        self._set_header_for_sector(sector_name)
        self._rebuild_sector_scene(sector_name)

    def select_local_node(self, local_name, initial=False):
        if local_name not in self.local_lookup:
            return

        self.selected_local_name = local_name
        selected_node = self.local_buttons[local_name]
        current_local = self.current_local_by_sector.get(self.active_sector_name, local_name)
        current_node = self.local_buttons.get(current_local, selected_node)
        selected_scale = getattr(selected_node, "ring_scale", max(selected_node.scale_x, selected_node.scale_y))
        current_scale = getattr(current_node, "ring_scale", max(current_node.scale_x, current_node.scale_y))

        self.local_selection_ring.position = selected_node.position
        self.local_selection_ring.scale = selected_scale * 2.7
        self.local_current_ring.position = current_node.position
        self.local_current_ring.scale = current_scale * 3.0
        self.local_selection_marker.position = selected_node.position
        self.local_selection_marker.scale = selected_scale * 3.0
        self.local_current_marker.position = current_node.position
        self.local_current_marker.scale = current_scale * 2.6
        self._update_local_panel(local_name)
        self._refresh_local_route_preview()

        if not initial:
            self.local_selection_marker.animate_scale(selected_scale * 3.4, duration=0.12)
            invoke(setattr, self.local_selection_marker, "scale", selected_scale * 3.0, delay=0.12)

    def _build_background_starfield(self):
        rng = random.Random(27)

        for _ in range(120):
            star_size = rng.uniform(0.0016, 0.0068)
            star = Entity(
                parent=self.starfield_parent,
                model="sphere",
                position=(rng.uniform(-0.54, 0.54), rng.uniform(-0.35, 0.35), rng.uniform(-0.075, -0.008)),
                scale=star_size,
                color=C(
                    rng.randint(112, 180),
                    rng.randint(166, 222),
                    255,
                    rng.randint(28, 94),
                ),
            )

            if rng.random() > 0.76:
                Entity(
                    parent=star,
                    model="sphere",
                    scale=3.1,
                    color=C(90, 160, 255, 14),
                )

        for offset in (-0.24, 0.24):
            Entity(
                parent=self.galaxy_layer,
                model="quad",
                position=(0, offset, -0.018),
                scale=(0.80, 0.0016),
                color=C(92, 126, 172, 10),
            )

        for offset in (-0.24, 0.24):
            Entity(
                parent=self.galaxy_layer,
                model="quad",
                position=(offset, 0, -0.018),
                scale=(0.0016, 0.58),
                color=C(92, 126, 172, 10),
            )

        for angle in (22, -26, 64):
            Entity(
                parent=self.galaxy_layer,
                model="quad",
                position=(0, 0, -0.019),
                scale=(0.92, 0.0015),
                rotation_z=angle,
                color=C(88, 138, 212, 10),
            )

    def _build_nebulae(self):
        rng = random.Random(343)
        nebula_specs = (
            ((-0.32, 0.20), (0.42, 0.26), C(62, 112, 240, 20)),
            ((0.18, 0.25), (0.34, 0.24), C(138, 86, 255, 16)),
            ((0.26, -0.14), (0.30, 0.22), C(255, 122, 88, 14)),
            ((-0.06, -0.24), (0.36, 0.24), C(56, 212, 188, 10)),
        )

        for position, scale_value, tint in nebula_specs:
            for layer_index in range(5):
                Entity(
                    parent=self.sector_fog_parent,
                    model="sphere",
                    position=(
                        position[0] + (layer_index - 2) * 0.018,
                        position[1] + sin(layer_index * 1.7) * 0.014,
                        -0.030 - layer_index * 0.006,
                    ),
                    scale=(scale_value[0] * (0.30 + layer_index * 0.07), scale_value[1] * (0.22 + layer_index * 0.06), 0.015),
                    color=C(*tint.rgba32[:3], max(5, tint.rgba32[3] // 3)),
                )

            for _ in range(18):
                Entity(
                    parent=self.sector_fog_parent,
                    model="sphere",
                    position=(
                        position[0] + rng.uniform(-scale_value[0] * 0.34, scale_value[0] * 0.34),
                        position[1] + rng.uniform(-scale_value[1] * 0.28, scale_value[1] * 0.28),
                        rng.uniform(-0.072, -0.040),
                    ),
                    rotation_z=rng.uniform(-45, 45),
                    scale=(rng.uniform(0.025, 0.095), rng.uniform(0.006, 0.024), 0.004),
                    color=C(*tint.rgba32[:3], rng.randint(5, 16)),
                )

    def _build_cluster_labels(self):
        cluster_specs = (
            ("ВНУТРЕННИЕ РУБЕЖИ", (-0.30, 0.12), 0.48),
            ("ПРИЗРАЧНЫЙ ПРОСТОР", (0.18, 0.24), 0.46),
            ("ПЕПЕЛЬНАЯ ГРАНИЦА", (0.18, -0.22), 0.44),
            ("ЧЁРНЫЙ ДРЕЙФ", (-0.28, -0.31), 0.43),
        )

        for label, position, scale_value in cluster_specs:
            Text(
                parent=self.galaxy_layer,
                text=label,
                position=(position[0], position[1], -0.027),
                scale=scale_value,
                color=C(96, 140, 202, 36),
                font=TITLE_FONT,
            )

    def _build_route_graph(self):
        graph = {entry["name"]: [] for entry in GALAXY_SYSTEMS}
        # Routes are authored hyperspace corridors, not "nearest point" links.
        # This keeps travel readable: Valkyr -> Cygnus Gate -> Perseus Veil.
        for start_name, end_name in GALAXY_ROUTES:
            distance = self._system_distance(start_name, end_name)
            graph.setdefault(start_name, []).append((end_name, distance))
            graph.setdefault(end_name, []).append((start_name, distance))
        return graph

    def _system_distance(self, start_name, end_name):
        start = Vec2(*self._map_position(start_name))
        end = Vec2(*self._map_position(end_name))
        return (end - start).length()

    def _find_route_path(self, start_name, end_name):
        if start_name == end_name:
            return [start_name]

        queue = [(start_name, [start_name])]
        visited = {start_name}
        while queue:
            current_name, path = queue.pop(0)
            for next_name, _edge_cost in self.route_graph.get(current_name, ()):
                if next_name in visited:
                    continue
                next_path = path + [next_name]
                if next_name == end_name:
                    return next_path
                visited.add(next_name)
                queue.append((next_name, next_path))

        return [start_name, end_name]

    def _build_routes(self):
        self.background_routes = []
        return
        for start_name, end_name in GALAXY_ROUTES:
            start = self._map_position(start_name)
            end = self._map_position(end_name)
            route_shadow = make_route_line(
                self.routes_parent,
                start,
                end,
                tint=C(46, 84, 134, 26),
                thickness=0.010,
                z=-0.028,
            )
            route_outer = make_route_line(
                self.routes_parent,
                start,
                end,
                tint=C(78, 126, 194, 46),
                thickness=0.0055,
                z=-0.027,
            )
            route_inner = make_route_line(
                self.routes_parent,
                start,
                end,
                tint=C(126, 182, 238, 88),
                thickness=0.0018,
                z=-0.026,
            )
            self.background_routes.extend((route_shadow, route_outer, route_inner))

    def _build_systems(self):
        for index, entry in enumerate(GALAXY_SYSTEMS):
            position = self._map_position(entry["name"])
            depth = self._map_depth(entry["name"])
            self._make_depth_shadow(
                self.system_parent,
                position,
                entry["tint"],
                width=entry["size"] * 4.4,
                height=entry["size"] * 1.55,
                z=-0.066 + depth,
                rotation=index * 11,
            )
            make_holo_ellipse(
                self.system_parent,
                position,
                entry["size"] * 2.30,
                entry["size"] * 1.05,
                self._color_from_tint(entry["tint"], 70),
                thickness=0.0018,
                z=-0.046 + depth,
                segments=18,
                rotation=0.24 + index * 0.10,
            )
            Entity(
                parent=self.system_parent,
                model="cube",
                position=(position[0], position[1], -0.048 + depth),
                scale=(0.13, 0.006, 0.006),
                color=C(*entry["tint"].rgba32[:3], 34),
            )
            node = Button(
                parent=self.system_parent,
                model="sphere",
                position=(position[0], position[1], -0.035 + depth),
                scale=entry["size"] * 1.08,
                color=entry["tint"],
                highlight_scale=1.12,
                pressed_scale=0.94,
            )
            node.base_scale = entry["size"] * 1.08
            node.base_tint = entry["tint"]
            node.system_name = entry["name"]
            node.on_click = Func(self.enter_sector, entry["name"])
            self.system_buttons[entry["name"]] = node
            self._decorate_sector_node(node, entry, index, depth)

            glow = Entity(
                parent=node,
                model="sphere",
                scale=3.2,
                color=C(*entry["tint"].rgba32[:3], 28),
            )
            glow.phase_offset = index * 0.65
            glow.base_scale = 2.5
            self.node_glows.append(glow)
            Entity(
                parent=node,
                model="sphere",
                scale=0.38,
                color=C(250, 252, 255, 184),
            )

            label_offset_x = -0.13 if position[0] > 0.22 else 0.026
            label = Text(
                parent=self.system_parent,
                text=entry["name"],
                position=(position[0] + label_offset_x, position[1] + 0.012),
                scale=0.46,
                color=C(182, 208, 238, 194),
                font=TECH_FONT,
            )
            label.z = -0.04

    def open(self):
        global map_message_timer
        if self.is_open:
            return

        self.is_open = True
        self.root.enabled = True
        self._apply_layout()
        map_message_timer = 0
        self.show_galaxy_view(initial=True)
        set_controls_hint_state(False)
        set_text_block_state(map_message_text, map_message_panel, False)
        freeze_first_person()
        default_crosshair.enabled = False
        npc_crosshair.enabled = False

    def close(self):
        if not self.is_open:
            return

        self.is_open = False
        self.root.enabled = False
        restore_first_person()
        set_controls_hint_state(True)
        default_crosshair.enabled = True
        npc_crosshair.enabled = False

    def set_zoom(self, new_zoom):
        self.zoom = clamp(new_zoom, self.min_zoom, self.max_zoom)
        self.map_content.scale = self.map_base_scale * self.zoom
        self._clamp_pan()

    def _clamp_pan(self):
        limit_x = self.pan_limit_x * self.zoom
        limit_y = self.pan_limit_y * self.zoom
        self.map_content.x = clamp(self.map_content.x, -limit_x, limit_x)
        self.map_content.y = clamp(self.map_content.y, -limit_y + self.map_base_y, limit_y + self.map_base_y)

    def _route_status(self):
        if self.selected_system_name == self.current_system_name:
            return "Текущий сектор уже активен. Выбери другой сектор или открой его локальную схему кликом."
        return f"Выбран сектор: {self.selected_system_name}. Enter делает его текущим, а ЛКМ открывает внутреннюю карту."

    def _refresh_route_preview(self):
        if self.route_preview:
            destroy(self.route_preview)
            self.route_preview = None

        if self.selected_system_name == self.current_system_name:
            return

        path = self._find_route_path(self.current_system_name, self.selected_system_name)
        self.route_preview = Entity(parent=self.map_content)
        points = [Vec3(*self._map_position(node_name), -0.032) for node_name in path]
        build_route_polyline(
            self.route_preview,
            points,
            color_value=(0.26, 0.78, 1.0, 0.22),
            thickness=9.0,
            name="galaxy_route_glow",
        )
        build_route_polyline(
            self.route_preview,
            points,
            color_value=(0.72, 0.92, 1.0, 0.94),
            thickness=3.4,
            name="galaxy_route_core",
        )

        for node_name in path[1:-1]:
            point = self._map_position(node_name)
            Entity(
                parent=self.route_preview,
                model="sphere",
                position=(point[0], point[1], -0.033),
                scale=0.045,
                color=C(160, 230, 255, 128),
            )

        end = self._map_position(self.selected_system_name)
        Entity(
            parent=self.route_preview,
            model="sphere",
            position=(end[0], end[1], -0.033),
            scale=0.11,
            color=C(110, 220, 255, 44),
        )

    def _refresh_current_ship_marker(self, target_name):
        current_position = self._map_position(self.current_system_name)
        target_position = self._map_position(target_name)
        self.current_ship_marker.position = (current_position[0], current_position[1], -0.050)
        direction = Vec2(target_position[0] - current_position[0], target_position[1] - current_position[1])
        if direction.length() > 0.001:
            self.current_ship_marker.rotation_z = degrees(atan2(direction.y, direction.x))

    def select_system(self, system_name, initial=False):
        self.selected_system_name = system_name
        selected_node = self.system_buttons[system_name]
        current_node = self.system_buttons[self.current_system_name]

        self.selection_ring.position = selected_node.position
        self.selection_ring.scale = selected_node.base_scale * 2.8
        self.selection_marker.position = selected_node.position
        self.selection_marker.scale = selected_node.base_scale * 4.6
        self.current_ring.position = current_node.position
        self.current_ring.scale = current_node.base_scale * 3.2
        self._refresh_current_ship_marker(system_name)

        self._update_galaxy_panel(system_name)
        self._refresh_route_preview()

        if not initial:
            self.selection_marker.animate_scale(selected_node.base_scale * 5.3, duration=0.12)
            invoke(setattr, self.selection_marker, "scale", selected_node.base_scale * 4.6, delay=0.12)

    def plot_course(self):
        if self.view_mode == "sector":
            current_local = self.current_local_by_sector.get(self.active_sector_name)
            if self.selected_local_name == current_local:
                set_wrapped_text(self.route_text, "Этот узел уже активен. Выбери другую точку внутри сектора для перестройки маршрута.", self.info_wrap)
                return

            self.current_local_by_sector[self.active_sector_name] = self.selected_local_name
            self.location_text.text = f"Текущий узел: {self.selected_local_name}"
            set_wrapped_text(self.route_text, f"Внутрисекторный маршрут перестроен. Активная точка: «{self.selected_local_name}».", self.info_wrap)
            self.select_local_node(self.selected_local_name, initial=True)
            return

        if self.selected_system_name == self.current_system_name:
            set_wrapped_text(self.route_text, "Ты уже находишься в этом секторе. Выбери другой сектор или войди в него кликом.", self.info_wrap)
            return

        self.current_system_name = self.selected_system_name
        self.location_text.text = f"Текущий сектор: {self.current_system_name}"
        set_wrapped_text(self.route_text, f"Секторный курс согласован. Маркер перенесён в сектор «{self.current_system_name}».", self.info_wrap)
        self.select_system(self.current_system_name, initial=True)

    def update(self):
        if not self.is_open:
            return

        self.pulse_time += time.dt * 2.3
        self.inner_ring.rotation_z += time.dt * 18
        self.mid_ring.rotation_z -= time.dt * 11
        self.outer_ring.rotation_z += time.dt * 6
        self.scan_ring.rotation_z -= time.dt * 3.5
        self.holo_core.scale_x = 0.96 + sin(self.pulse_time * 0.55) * 0.03
        self.holo_core.scale_y = 0.76 + sin(self.pulse_time * 0.48) * 0.02
        self.galaxy_disk.scale_x = 0.88 + sin(self.pulse_time * 0.38) * 0.015
        self.galaxy_disk.scale_y = 0.88 + sin(self.pulse_time * 0.52) * 0.020
        self.selection_ring.rotation_z -= time.dt * 24
        self.selection_marker.rotation_z -= time.dt * 18
        self.current_ring.rotation_z += time.dt * 18
        self.local_selection_ring.rotation_z -= time.dt * 24
        self.local_selection_marker.rotation_z -= time.dt * 18
        self.local_current_ring.rotation_z += time.dt * 18
        self.local_current_marker.rotation_z += time.dt * 13
        self.local_system_plane.rotation_z += time.dt * 1.8
        self.local_scan_line.y = -0.30 + ((self.pulse_time * 0.12) % 0.62)
        for glow in self.node_glows:
            glow.scale = glow.base_scale + sin(self.pulse_time + glow.phase_offset) * 0.18
        for glow in self.local_glows:
            glow.scale = glow.base_scale + sin(self.pulse_time + glow.phase_offset) * 0.16

        hovered = mouse.hovered_entity
        if self.view_mode == "galaxy":
            hovered_name = getattr(hovered, "system_name", None)
            if hovered_name and hovered_name != self.hovered_system_name:
                self.hovered_system_name = hovered_name
                if hovered_name != self.selected_system_name:
                    self.select_system(hovered_name, initial=True)
            elif not hovered_name and self.hovered_system_name is not None:
                self.hovered_system_name = None
        else:
            hovered_local = getattr(hovered, "local_name", None)
            if hovered_local and hovered_local != self.hovered_local_name:
                self.hovered_local_name = hovered_local
                if hovered_local != self.selected_local_name:
                    self.select_local_node(hovered_local, initial=True)
            elif not hovered_local and self.hovered_local_name is not None:
                self.hovered_local_name = None

        if held_keys["right mouse"] or held_keys["middle mouse"]:
            self.pan_map(mouse.velocity[0] * 2.8, mouse.velocity[1] * 2.8)

        keyboard_pan_speed = time.dt * (0.44 if held_keys["shift"] else 0.28)
        if held_keys["a"] or held_keys["left arrow"]:
            self.pan_map(keyboard_pan_speed, 0)
        if held_keys["d"] or held_keys["right arrow"]:
            self.pan_map(-keyboard_pan_speed, 0)
        if held_keys["w"] or held_keys["up arrow"]:
            self.pan_map(0, -keyboard_pan_speed)
        if held_keys["s"] or held_keys["down arrow"]:
            self.pan_map(0, keyboard_pan_speed)

    def input(self, key):
        if not self.is_open:
            return False

        if key in ("escape", "tab"):
            if self.view_mode == "sector":
                self.show_galaxy_view()
                return True
            self.close()
            return True

        if key == "scroll up":
            self.set_zoom(self.zoom * 1.1)
            return True

        if key == "scroll down":
            self.set_zoom(self.zoom / 1.1)
            return True

        if key == "enter":
            self.plot_course()
            return True

        if key == "r":
            self.set_zoom(1.0 if self.view_mode == "galaxy" else 1.06)
            self._reset_pan()
            return True

        return False


def queue_galaxy_map():
    global map_open_queued
    if galaxy_map.is_open or map_open_queued:
        return

    map_open_queued = True
    show_map_message()

    def _open():
        global map_open_queued
        map_open_queued = False
        galaxy_map.open()

    invoke(_open, delay=MAP_OPEN_DELAY)


build_space_sky()
interior_parts = build_ship_interior()

AmbientLight(color=C(120, 140, 170, 72))
PointLight(position=(0, 3, 0), color=C(90, 140, 220, 38))

command_console = Entity(
    model="cube",
    position=(0, -0.1, 1.5),
    scale=(2.2, 1.4, 1.2),
    color=C(24, 52, 108),
    texture=ship_panel_texture,
    texture_scale=(2, 2),
    collider="box",
)

console_screen = Entity(
    parent=command_console,
    model="cube",
    position=(0, 0.35, -0.45),
    scale=(1.4, 0.5, 0.08),
    color=C(24, 115, 170),
    texture=console_screen_texture,
)
console_screen.emissive_color = C(0, 170, 210, 140)

if droid_model_asset:
    droid = Entity(
        model=droid_model_asset,
        position=(ROOM_HALF_SIZE - 2.7, -0.2, ROOM_HALF_SIZE - 2.4),
        rotation=(0, 180, 0),
        scale=1.4,
        color=C(146, 156, 176),
        collider="box",
    )
else:
    droid = Entity(
        model="sphere",
        position=(ROOM_HALF_SIZE - 2.5, 0.2, ROOM_HALF_SIZE - 2.5),
        scale=1.3,
        color=C(140, 146, 160),
        collider="box",
    )

if not droid_model_asset:
    Entity(
        parent=droid,
        model="sphere",
        position=(0, 0.12, -0.55),
        scale=0.22,
        color=C(170, 60, 70),
    )

droid.base_y = droid.y
droid.base_rotation_y = droid.rotation_y

crew_hit_proxy = None
using_r2_droid = r2_droid_model_asset is not None and technician_model_asset == r2_droid_model_asset
using_poly_robot = poly_pizza_robot_model_asset is not None and technician_model_asset == poly_pizza_robot_model_asset
using_rigged_simple = rigged_simple_model_asset is not None and technician_model_asset == rigged_simple_model_asset

if using_r2_droid:
    crew_contact = Entity(
        model="cube",
        position=(-3.6, -0.08, 2.0),
        rotation=(0, 24, 0),
        scale=(1.05, 1.25, 0.95),
        color=C(255, 255, 255, 0),
        collider="box",
    )
    crew_contact_mesh = Entity(
        parent=crew_contact,
        position=(0, -0.28, 0),
    )
    crew_body = Entity(
        parent=crew_contact_mesh,
        model="cylinder",
        position=(0, 0.18, 0),
        scale=(0.72, 0.52, 0.72),
        color=C(94, 104, 120),
        texture=ship_panel_texture,
        texture_scale=(2, 1.5),
    )
    crew_head_shell = Entity(
        parent=crew_contact_mesh,
        model="sphere",
        position=(0, 0.52, 0),
        scale=(0.58, 0.28, 0.58),
        color=C(110, 120, 138),
        texture=ship_panel_texture,
        texture_scale=(1.6, 1.2),
    )
    crew_head_panel = Entity(
        parent=crew_contact_mesh,
        model="cube",
        position=(0, 0.46, 0.23),
        scale=(0.26, 0.12, 0.05),
        color=C(54, 72, 104),
        texture=console_panel_texture,
        texture_scale=(1.2, 1.2),
    )
    crew_left_leg = Entity(
        parent=crew_contact_mesh,
        model="cube",
        position=(-0.36, 0.10, 0),
        scale=(0.14, 0.46, 0.18),
        rotation=(0, 0, -10),
        color=C(92, 102, 118),
        texture=ship_panel_texture,
        texture_scale=(1, 2),
    )
    crew_right_leg = Entity(
        parent=crew_contact_mesh,
        model="cube",
        position=(0.36, 0.10, 0),
        scale=(0.14, 0.46, 0.18),
        rotation=(0, 0, 10),
        color=C(92, 102, 118),
        texture=ship_panel_texture,
        texture_scale=(1, 2),
    )
    crew_center_foot = Entity(
        parent=crew_contact_mesh,
        model="cube",
        position=(0, -0.08, 0.12),
        scale=(0.16, 0.18, 0.18),
        color=C(82, 90, 108),
        texture=ship_panel_texture,
        texture_scale=(1, 1),
    )
    crew_base_plate = Entity(
        parent=crew_contact_mesh,
        model="quad",
        position=(0, -0.14, 0),
        rotation=(90, 0, 0),
        scale=(0.30, 0.22),
        color=C(10, 18, 32, 86),
        texture=radial_gradient_texture,
    )
    crew_contact.look_yaw_offset = 0
    crew_attachment_root = crew_contact_mesh
elif using_poly_robot:
    crew_contact = Entity(
        position=(-3.6, -0.10, 2.0),
        rotation=(0, 24, 0),
    )
    crew_hit_proxy = Entity(
        parent=crew_contact,
        model="cube",
        scale=(1.02, 1.58, 0.94),
        color=C(255, 255, 255, 0),
        collider="box",
    )
    crew_contact_mesh = Entity(
        parent=crew_contact,
        model=technician_model_asset,
        position=(0.0, -0.82, 0.01),
        rotation=(0, 180, 0),
        scale=0.50,
    )
    crew_contact.look_yaw_offset = 180
    crew_contact.animation_profile = "poly_robot_idle_scan"
    crew_attachment_root = crew_contact
elif using_rigged_simple:
    crew_contact = Entity(
        model=technician_model_asset,
        position=(-3.6, 0.03, 2.0),
        rotation=(0, 24, 0),
        scale=0.17,
        color=C(88, 102, 124),
        collider="box",
    )
    crew_contact_mesh = crew_contact
    crew_contact.look_yaw_offset = 0
    crew_attachment_root = crew_contact_mesh
elif technician_model_asset:
    crew_contact = Entity(
        model=technician_model_asset,
        position=(-3.6, 0.76, 2.0),
        rotation=(0, 205, 0),
        scale=1.0,
        collider="box",
    )
    crew_contact_mesh = crew_contact
    crew_contact.look_yaw_offset = 0
    crew_attachment_root = crew_contact_mesh
else:
    crew_contact = Entity(
        model="cube",
        position=(-3.6, -0.1, 2.0),
        scale=(0.75, 1.6, 0.58),
        color=C(58, 74, 96),
        texture=ship_panel_texture,
        texture_scale=(1, 2),
        collider="box",
    )
    crew_contact_mesh = crew_contact
    crew_contact.look_yaw_offset = 0
    crew_attachment_root = crew_contact_mesh

crew_contact.npc_name = "Бортовой техник"
crew_contact.npc_brain = ShipTechnicianMind()
crew_contact.base_y = crew_contact.y
crew_contact.base_rotation_y = crew_contact.rotation_y
crew_contact_light = PointLight(
    parent=crew_contact,
    position=(0.0, 1.10 if using_poly_robot else 0.72, -0.20),
    color=C(96, 156, 255, 26),
)

if not technician_model_asset:
    Entity(
        parent=crew_contact,
        model="sphere",
        position=(0, 0.78, 0.02),
        scale=0.64,
        color=C(84, 102, 128),
    )

crew_visor = Entity(
    parent=crew_attachment_root,
    model="cube",
    position=(0.0, 0.48, 0.22) if using_r2_droid else ((0.0, 0.36, 0.18) if using_poly_robot else ((0.0, 3.8, 1.0) if using_rigged_simple else (0.0, 0.78 if technician_model_asset else 0.75, 0.22 if technician_model_asset else 0.31))),
    scale=(0.16, 0.06, 0.06) if using_r2_droid else ((0.14, 0.04, 0.03) if using_poly_robot else ((1.1, 0.28, 0.18) if using_rigged_simple else ((0.22, 0.07, 0.04) if technician_model_asset else (0.34, 0.12, 0.05)))),
    color=C(98, 210, 255),
)
crew_visor.emissive_color = C(98, 210, 255, 160)
crew_visor_base_scale = Vec3(crew_visor.scale_x, crew_visor.scale_y, crew_visor.scale_z)

crew_chest_light = Entity(
    parent=crew_attachment_root,
    model="cube",
    position=(0.0, 0.08, 0.27) if using_r2_droid else ((0.0, 0.12, 0.19) if using_poly_robot else ((0.0, 1.7, 0.95) if using_rigged_simple else (0.0, 0.30 if technician_model_asset else 0.20, 0.16 if technician_model_asset else 0.30))),
    scale=(0.10, 0.12, 0.06) if using_r2_droid else ((0.10, 0.08, 0.04) if using_poly_robot else ((0.55, 0.55, 0.16) if using_rigged_simple else ((0.10, 0.10, 0.03) if technician_model_asset else (0.18, 0.18, 0.05)))),
    color=C(90, 190, 235),
)
crew_chest_light.emissive_color = C(90, 190, 235, 150)
if using_poly_robot:
    crew_visor.enabled = False
    crew_chest_light.enabled = False

crew_datapad_mount = Entity(
    parent=crew_attachment_root,
    position=(0.34, 0.12, 0.16) if using_r2_droid else ((0.30, 0.06, 0.20) if using_poly_robot else ((1.1, 1.0, 1.0) if using_rigged_simple else (0.18, 0.46 if technician_model_asset else 0.42, 0.18))),
    rotation=(0, -8, -4) if using_r2_droid else (8, -28, -12),
)
crew_datapad_body = Entity(
    parent=crew_datapad_mount,
    model="cube",
    scale=(0.18, 0.26, 0.04) if using_r2_droid else ((0.30, 0.42, 0.05) if using_poly_robot else ((1.25, 1.7, 0.18) if using_rigged_simple else (0.20, 0.28, 0.03))),
    color=C(26, 34, 52),
)
crew_datapad_frame = Entity(
    parent=crew_datapad_mount,
    model="cube",
    position=(0, 0, 0.015) if using_r2_droid else ((0, 0, 0.020) if using_poly_robot else ((0, 0, 0.07) if using_rigged_simple else (0, 0, 0.012))),
    scale=(0.14, 0.20, 0.028) if using_r2_droid else ((0.24, 0.34, 0.03) if using_poly_robot else ((1.05, 1.4, 0.08) if using_rigged_simple else (0.17, 0.23, 0.01))),
    color=C(40, 70, 118),
)
crew_datapad_screen = Entity(
    parent=crew_datapad_mount,
    model="cube",
    position=(0, 0, 0.025) if using_r2_droid else ((0, 0, 0.028) if using_poly_robot else ((0, 0, 0.11) if using_rigged_simple else (0, 0, 0.02))),
    scale=(0.11, 0.16, 0.010) if using_r2_droid else ((0.20, 0.28, 0.012) if using_poly_robot else ((0.88, 1.18, 0.03) if using_rigged_simple else (0.145, 0.20, 0.004))),
    color=C(72, 198, 245),
)
crew_datapad_screen.emissive_color = C(72, 198, 245, 170)
crew_datapad_indicator = Entity(
    parent=crew_datapad_mount,
    model="sphere",
    position=(0.04, 0.06, 0.022) if using_r2_droid else ((0.08, 0.10, 0.032) if using_poly_robot else ((0.45, 0.55, 0.12) if using_rigged_simple else (0.06, 0.08, 0.025))),
    scale=0.018 if using_r2_droid else (0.028 if using_poly_robot else (0.12 if using_rigged_simple else 0.02)),
    color=C(255, 210, 120),
)
crew_datapad_indicator.emissive_color = C(255, 210, 120, 170)
crew_datapad_base_position = Vec3(crew_datapad_mount.position)
crew_datapad_base_rotation = Vec3(crew_datapad_mount.rotation_x, crew_datapad_mount.rotation_y, crew_datapad_mount.rotation_z)
crew_mesh_base_position = Vec3(crew_contact_mesh.position)
crew_mesh_base_rotation = Vec3(crew_contact_mesh.rotation_x, crew_contact_mesh.rotation_y, crew_contact_mesh.rotation_z)

for npc_part in (
    crew_contact_mesh,
    crew_visor,
    crew_chest_light,
    crew_datapad_mount,
    crew_datapad_body,
    crew_datapad_frame,
    crew_datapad_screen,
    crew_datapad_indicator,
):
    npc_part.npc_owner = crew_contact

if crew_hit_proxy:
    crew_hit_proxy.npc_owner = crew_contact

player = FirstPersonController(
    position=(0, 1, -7),
    speed=5,
    jump_height=1.2,
)
player.cursor.enabled = False
player.cursor.visible = False
player.gravity = 0.5

crosshair_root = make_ui_root(enabled=True)
default_crosshair, npc_crosshair = build_crosshair(parent=crosshair_root)
hud_root = make_ui_root(enabled=True)

map_message_panel = Entity(
    parent=hud_root,
    model="quad",
    position=(0, 0.08),
    scale=(0.36, 0.062),
    color=C(3, 10, 22, 224),
    texture=console_panel_texture,
    enabled=False,
)
map_message_text = Text(
    text="Открытие карты галактики...",
    parent=hud_root,
    position=(0, 0.08),
    origin=(0, 0),
    scale=0.72,
    color=C(125, 220, 255, 235),
    font=TITLE_FONT,
    enabled=False,
)

controls_panel = Entity(
    parent=hud_root,
    model="quad",
    position=(-0.26, -0.46),
    scale=(0.82, 0.052),
    color=C(3, 10, 22, 196),
    texture=console_panel_texture,
)
controls_hint = Text(
    text="WASD движение  |  Мышь обзор  |  E взаимодействие  |  ESC пауза  |  ЛКМ взмах мечом",
    parent=hud_root,
    position=(-0.46, -0.46),
    scale=0.48,
    color=C(205, 220, 242, 214),
    font=TECH_FONT,
)

interaction_panel = Entity(
    parent=hud_root,
    model="quad",
    position=(0, -0.17),
    scale=(0.36, 0.058),
    color=C(3, 10, 22, 214),
    texture=console_panel_texture,
    enabled=False,
)
interaction_text = Text(
    text="",
    parent=hud_root,
    position=(0, -0.17),
    origin=(0, 0),
    scale=0.70,
    color=C(140, 224, 255, 220),
    font=TITLE_FONT,
    enabled=False,
)
apply_text_role(interaction_text, "hud_title", multiplier=1.00, color_value=C(140, 224, 255, 220), font_value=TITLE_FONT)


def apply_hud_layout():
    safe_left, safe_right, safe_top, safe_bottom = ui_scale_manager.safe_rect()
    safe_width = safe_right - safe_left
    panel_texture = console_panel_texture or ui_button_base_texture

    controls_width = clamp(safe_width * 0.62, 0.70, 1.02)
    controls_height = 0.050
    controls_x = safe_left + controls_width * 0.50
    controls_y = safe_bottom + 0.020
    controls_panel.position = (controls_x, controls_y)
    controls_panel.scale = (controls_width, controls_height)
    controls_panel.texture = panel_texture
    controls_panel.color = C(3, 10, 22, 196)
    controls_hint.position = (safe_left + 0.02, controls_y)
    apply_text_role(controls_hint, "hint", multiplier=1.02, color_value=C(205, 220, 242, 214), font_value=TECH_FONT)

    interaction_width = clamp(safe_width * 0.38, 0.34, 0.52)
    interaction_y = safe_bottom + 0.16
    interaction_panel.position = (0, interaction_y)
    interaction_panel.scale = (interaction_width, 0.058)
    interaction_panel.texture = panel_texture
    interaction_panel.color = C(3, 10, 22, 214)
    interaction_text.position = (0, interaction_y)
    apply_text_role(interaction_text, "hud_title", multiplier=1.00)

    map_message_width = clamp(safe_width * 0.34, 0.36, 0.56)
    map_message_y = safe_top - 0.11
    map_message_panel.position = (0, map_message_y)
    map_message_panel.scale = (map_message_width, 0.062)
    map_message_panel.texture = panel_texture
    map_message_panel.color = C(3, 10, 22, 224)
    map_message_text.position = (0, map_message_y)
    apply_text_role(map_message_text, "hud_title", multiplier=1.02, color_value=C(125, 220, 255, 235), font_value=TITLE_FONT)

    crosshair_scale = clamp(1.0 - ui_scale_manager.narrow_factor * 0.05 + ui_scale_manager.wide_factor * 0.02, 0.90, 1.06)
    default_crosshair.scale = (0.022 if crosshair_texture else 0.014) * crosshair_scale
    npc_crosshair.scale = (0.014 if npc_crosshair_texture else 0.010) * crosshair_scale


register_ui_layout(apply_hud_layout)
apply_hud_layout()

# Camera-local coordinates for the sword:
# X shifts the model left or right across the screen.
# Y lifts it up or down.
# Z pushes it closer to or farther from the camera.
saber_holder = Entity(
    parent=camera,
    position=(0.45, -0.45, 0.65),
    rotation=(25, -15, -8),
)

saber_handle = Entity(
    parent=saber_holder,
    model="cylinder",
    position=(0, -0.18, 0),
    scale=(0.05, 0.28, 0.05),
    color=C(74, 78, 90),
)

saber_blade = Entity(
    parent=saber_holder,
    model="cylinder",
    position=(0, 0.55, 0),
    scale=(0.035, 1.1, 0.035),
    color=C(88, 200, 255),
)
saber_blade.emissive_color = C(88, 200, 255)

saber_glow = Entity(
    parent=saber_holder,
    model="cylinder",
    position=(0, 0.55, 0),
    scale=(0.08, 1.12, 0.08),
    color=C(60, 160, 255, 42),
)
saber_glow.emissive_color = C(88, 200, 255)

raycast_ignore = tuple(interior_parts) + (
    player,
    saber_holder,
    saber_handle,
    saber_blade,
    saber_glow,
)

galaxy_map = GalaxyMapUI()
dialogue_ui = DialogueUI()
pause_menu = PauseMenu()
hover_npcs = (droid, crew_contact)
base.accept("window-event", handle_window_event)
base.win.setCloseRequestEvent("space-rpg-window-close")
base.accept("space-rpg-window-close", quit_game)
apply_display_settings()
invoke(apply_display_settings, delay=0.25)
normalize_ui_camera()
schedule_mouse_recapture(delays=(0.05, 0.20), foreground=True)


def update():
    global map_message_timer, world_motion_time

    stabilize_first_person_restore()
    pause_menu.update()
    if pause_menu.is_open:
        interaction_text.enabled = False
        interaction_panel.enabled = False
        return

    world_motion_time += time.dt
    droid.y = droid.base_y + sin(world_motion_time * 2.0) * 0.07
    droid.rotation_y = droid.base_rotation_y + world_motion_time * 24
    crew_contact.y = crew_contact.base_y + sin(world_motion_time * 1.7) * (0.018 if using_r2_droid else 0.025)
    crew_target_rotation = crew_contact.base_rotation_y + sin(world_motion_time * 0.9) * (6.0 if using_r2_droid else 3.5)
    player_offset = Vec2(player.x - crew_contact.x, player.z - crew_contact.z)
    if player_offset.length() < 5.4 or dialogue_ui.is_open:
        crew_target_rotation = degrees(atan2(player.x - crew_contact.x, player.z - crew_contact.z)) + getattr(crew_contact, "look_yaw_offset", 0)

    rotation_delta = ((crew_target_rotation - crew_contact.rotation_y + 180) % 360) - 180
    crew_contact.rotation_y += clamp(rotation_delta, -time.dt * 160, time.dt * 160)
    if using_r2_droid:
        crew_contact.rotation_z = sin(world_motion_time * 1.35) * 1.6
        crew_datapad_mount.position = crew_datapad_base_position + Vec3(0, sin(world_motion_time * 1.8) * 0.035, 0)
        crew_datapad_mount.rotation_x = crew_datapad_base_rotation.x
        crew_datapad_mount.rotation_y = -22 + sin(world_motion_time * 1.1) * 10.0
        crew_datapad_mount.rotation_z = -10 + sin(world_motion_time * 1.6) * 6.0
        crew_visor.scale_x = crew_visor_base_scale.x + sin(world_motion_time * 2.4) * 0.02
    elif using_poly_robot:
        crew_contact.rotation_z = sin(world_motion_time * 1.1) * 0.9
        crew_contact_mesh.position = crew_mesh_base_position + Vec3(0, sin(world_motion_time * 1.55) * 0.012, 0)
        crew_contact_mesh.rotation_x = crew_mesh_base_rotation.x + sin(world_motion_time * 1.25) * 1.6
        crew_contact_mesh.rotation_y = crew_mesh_base_rotation.y + sin(world_motion_time * 0.85) * 7.0
        crew_contact_mesh.rotation_z = crew_mesh_base_rotation.z + sin(world_motion_time * 1.05) * 1.2
        crew_datapad_mount.position = crew_datapad_base_position + Vec3(0, sin(world_motion_time * 1.8) * 0.018, 0)
        crew_datapad_mount.rotation_x = crew_datapad_base_rotation.x + sin(world_motion_time * 1.2) * 3.0
        crew_datapad_mount.rotation_y = crew_datapad_base_rotation.y + sin(world_motion_time * 1.0) * 5.0
        crew_datapad_mount.rotation_z = crew_datapad_base_rotation.z + sin(world_motion_time * 1.6) * 4.0
        crew_visor.scale_x = crew_visor_base_scale.x + sin(world_motion_time * 2.0) * 0.015
    else:
        crew_contact.rotation_z = 0
        crew_datapad_mount.position = crew_datapad_base_position
        crew_datapad_mount.rotation_x = crew_datapad_base_rotation.x
        crew_datapad_mount.rotation_y = crew_datapad_base_rotation.y
        crew_datapad_mount.rotation_z = crew_datapad_base_rotation.z + sin(world_motion_time * 1.6) * 4.0
        crew_visor.scale_x = crew_visor_base_scale.x
    crew_datapad_screen.color = C(72, 188 + int((sin(world_motion_time * 2.2) + 1) * 18), 245)
    crew_datapad_screen.emissive_color = C(72, 198 + int((sin(world_motion_time * 2.2) + 1) * 14), 245, 170)
    crew_visor.emissive_color = C(98, 210 + int((sin(world_motion_time * 2.4) + 1) * 12), 255, 170)

    galaxy_map.update()
    dialogue_ui.update()
    if galaxy_map.is_open:
        if map_message_text.enabled:
            set_text_block_state(map_message_text, map_message_panel, False)
        interaction_text.enabled = False
        interaction_panel.enabled = False
        return

    look_hit = current_target(distance=5)
    hit_entity = look_hit.entity if look_hit.hit else None
    hit_target = getattr(hit_entity, "npc_owner", hit_entity)

    if dialogue_ui.is_open:
        toggle_crosshair(False)
        interaction_text.enabled = False
        interaction_panel.enabled = False
    else:
        toggle_crosshair(hit_target in hover_npcs)

        if hit_entity == command_console:
            interaction_text.text = "E: открыть карту галактики"
            set_text_block_state(interaction_text, interaction_panel, True)
        elif hit_target == crew_contact:
            interaction_text.text = "E: поговорить"
            set_text_block_state(interaction_text, interaction_panel, True)
        else:
            set_text_block_state(interaction_text, interaction_panel, False)

    if map_message_timer > 0:
        map_message_timer -= time.dt
        if map_message_timer <= 0:
            set_text_block_state(map_message_text, map_message_panel, False)


def input(key):
    if pause_menu.input(key):
        return

    if dialogue_ui.input(key):
        return

    if galaxy_map.input(key):
        return

    if key in ("left mouse down", "right mouse down", "middle mouse down") and wants_gameplay_mouse_capture():
        schedule_mouse_recapture(delays=(0.01, 0.10), foreground=True)

    if key == "escape":
        pause_menu.open()
        return

    if dialogue_ui.is_open:
        return

    if galaxy_map.is_open or map_open_queued:
        return

    if key == "left mouse down":
        swing_saber()

    if key == "e":
        look_hit = current_target(distance=4)
        if not look_hit.hit:
            return

        if look_hit.entity == command_console:
            queue_galaxy_map()
            return

        if getattr(look_hit.entity, "npc_owner", look_hit.entity) == crew_contact:
            dialogue_ui.open(crew_contact)


app.run()
