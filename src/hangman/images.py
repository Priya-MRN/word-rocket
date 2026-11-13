"""Word picture rewards as real emoji images (Twemoji).

The public entry point is :func:`image_url_for`, which maps an illustration id
(or raw word) to a **real PNG image URL** from Twemoji — the standard, open
emoji image set maintained by the community (https://github.com/jdecked/twemoji).
No hand-drawn SVG: each word resolves to a genuine emoji image such as a cat 🐱
or an apple 🍎.

The mapping is: word -> emoji character -> Twemoji codepoint filename -> URL.
Words with no known emoji fall back to a generic sparkle so there is always a
friendly picture. Building the URL is pure Python with no dependencies; only the
browser fetches the actual image at render time.
"""

from __future__ import annotations

# Twemoji 72x72 PNG assets, served from jsDelivr (a stable, standard CDN).
_TWEMOJI_BASE = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/"

# Fallback emoji used when a word has no dedicated mapping.
_FALLBACK_EMOJI = "🌟"


# Standard emoji keyed by common (lower-case) words / illustration ids.
_EMOJI = {
    "cat": "🐱", "dog": "🐶", "fish": "🐟", "apple": "🍎", "banana": "🍌",
    "sun": "☀️", "star": "⭐", "ball": "⚽", "tree": "🌳", "flower": "🌸",
    "house": "🏠", "car": "🚗", "bird": "🐦", "heart": "❤️", "moon": "🌙",
    "grapes": "🍇", "frog": "🐸", "duck": "🦆", "egg": "🥚", "milk": "🥛",
    "cow": "🐮", "pig": "🐷", "lion": "🦁", "bear": "🐻", "rabbit": "🐰",
    "bee": "🐝", "ant": "🐜", "owl": "🦉", "boat": "⛵", "kite": "🪁",
    "drum": "🥁", "book": "📖", "key": "🔑", "cup": "🥤", "hat": "🎩",
    "shoe": "👟", "leaf": "🍃", "rain": "🌧️", "snow": "❄️", "cake": "🎂",
    "orange": "🍊", "mango": "🥭", "lemon": "🍋", "rose": "🌹",

    # --- Animals ---------------------------------------------------------
    "hen": "🐔", "goat": "🐐", "horse": "🐴", "sheep": "🐑", "mouse": "🐭",
    "tiger": "🐯", "monkey": "🐵", "elephant": "🐘", "zebra": "🦓",
    "giraffe": "🦒", "deer": "🦌", "fox": "🦊", "wolf": "🐺", "snail": "🐌",
    "crab": "🦀", "whale": "🐳", "shark": "🦈", "dolphin": "🐬",
    "turtle": "🐢", "snake": "🐍", "parrot": "🦜", "penguin": "🐧",
    "panda": "🐼", "koala": "🐨", "camel": "🐫", "donkey": "🫏",
    "buffalo": "🐃", "squirrel": "🐿️", "bat": "🦇", "eagle": "🦅",
    "crow": "🐦‍⬛", "peacock": "🦚", "swan": "🦢", "rooster": "🐓",
    "turkey": "🦃", "goose": "🪿", "kitten": "🐈", "puppy": "🐕",
    "calf": "🐄", "lamb": "🐑", "chick": "🐤", "butterfly": "🦋",
    "spider": "🕷️", "ladybug": "🐞", "caterpillar": "🐛",
    "grasshopper": "🦗", "dragonfly": "🪰", "cricket": "🦗", "moth": "🦋",
    "worm": "🪱", "octopus": "🐙", "jellyfish": "🪼", "starfish": "⭐",
    "seal": "🦭", "lobster": "🦞", "shrimp": "🦐", "lizard": "🦎",
    "crocodile": "🐊", "hippo": "🦛", "rhino": "🦏", "kangaroo": "🦘",
    "leopard": "🐆", "cheetah": "🐆", "otter": "🦦", "beaver": "🦫",
    "hedgehog": "🦔", "raccoon": "🦝", "skunk": "🦨", "mole": "🐁",
    "badger": "🦡", "chipmunk": "🐿️", "hamster": "🐹", "ferret": "🦦",
    "llama": "🦙", "yak": "🐂", "bison": "🦬", "moose": "🫎",
    "antelope": "🦌", "gorilla": "🦍", "sloth": "🦥", "lemur": "🐒",
    "flamingo": "🦩", "pelican": "🦤", "seagull": "🕊️", "sparrow": "🐦",
    "robin": "🐦", "pigeon": "🕊️", "woodpecker": "🐦", "mosquito": "🦟",
    "eggplant": "🍆", "drumstick": "🥬",

    # --- Food ------------------------------------------------------------
    "cherry": "🍒", "peach": "🍑", "pear": "🍐", "plum": "🫐",
    "melon": "🍈", "kiwi": "🥝", "coconut": "🥥", "pineapple": "🍍",
    "strawberry": "🍓", "blueberry": "🫐", "guava": "🍈", "papaya": "🥭",
    "dates": "🌴", "bread": "🍞", "rice": "🍚", "cheese": "🧀",
    "butter": "🧈", "honey": "🍯", "soup": "🍲", "cookie": "🍪",
    "candy": "🍬", "icecream": "🍨", "pizza": "🍕", "pasta": "🍝",
    "noodles": "🍜", "sandwich": "🥪", "burger": "🍔", "salad": "🥗",
    "carrot": "🥕", "potato": "🥔", "tomato": "🍅", "onion": "🧅",
    "garlic": "🧄", "peas": "🫛", "beans": "🫘", "corn": "🌽",
    "pumpkin": "🎃", "cabbage": "🥬", "spinach": "🥬", "cucumber": "🥒",
    "lettuce": "🥬", "mushroom": "🍄", "ginger": "🫚", "chilli": "🌶️",
    "sugar": "🍬", "salt": "🧂", "water": "💧", "juice": "🧃", "tea": "🍵",
    "coffee": "☕", "curd": "🥛", "cream": "🍦", "jam": "🍓",
    "pancake": "🥞", "waffle": "🧇", "donut": "🍩", "muffin": "🧁",
    "pie": "🥧", "pudding": "🍮", "chocolate": "🍫", "popcorn": "🍿",
    "chips": "🍟", "nuts": "🥜", "almond": "🌰", "cashew": "🥜",
    "peanut": "🥜", "dosa": "🥞", "idli": "🍚", "samosa": "🥟",
    "chapati": "🫓", "porridge": "🥣", "yogurt": "🥛", "oats": "🌾",
    "wheat": "🌾", "flour": "🌾", "oil": "🫒", "vinegar": "🧴",
    "pepper": "🌶️", "cinnamon": "🪵", "lentils": "🫘", "beetroot": "🥬",
    "radish": "🥬", "turnip": "🥬", "broccoli": "🥦", "cauliflower": "🥦",
    "celery": "🥬", "olive": "🫒", "berry": "🫐", "apricot": "🍑",
    "fig": "🍇", "pomegranate": "🍎", "jackfruit": "🍈", "lime": "🍋",
    "snack": "🍿", "breakfast": "🍳",

    # --- Nature / space --------------------------------------------------
    "root": "🌱", "seed": "🌱", "branch": "🌿", "grass": "🌱",
    "bush": "🌳", "lily": "🌷", "tulip": "🌷", "sunflower": "🌻",
    "daisy": "🌼", "lotus": "🪷", "cactus": "🌵", "palm": "🌴",
    "bamboo": "🎋", "fern": "🌿", "moss": "🌿", "vine": "🌿",
    "hill": "⛰️", "mountain": "🏔️", "valley": "🏞️", "river": "🏞️",
    "lake": "🏞️", "pond": "💧", "ocean": "🌊", "sea": "🌊",
    "beach": "🏖️", "sand": "🏖️", "rock": "🪨", "stone": "🪨",
    "cave": "🕳️", "island": "🏝️", "forest": "🌲", "desert": "🏜️",
    "field": "🌾", "garden": "🌷", "sky": "🌌", "cloud": "☁️",
    "earth": "🌍", "planet": "🪐", "comet": "☄️", "galaxy": "🌌",
    "space": "🌌", "rocket": "🚀", "sunset": "🌇", "sunrise": "🌅",
    "shadow": "🌑", "light": "💡", "fire": "🔥", "wave": "🌊",
    "shell": "🐚", "coral": "🪸", "pebble": "🪨", "mud": "🟤",
    "soil": "🟫", "clay": "🟤", "dust": "💨", "smoke": "💨",
    "stream": "🏞️", "waterfall": "🏞️", "spring": "💧", "well": "🕳️",
    "meadow": "🌾", "jungle": "🌴", "swamp": "🐊", "cliff": "🧗",
    "peak": "🏔️", "volcano": "🌋", "glacier": "🧊", "iceberg": "🧊",
    "horizon": "🌅", "nature": "🌿", "season": "🍂", "summer": "☀️",
    "winter": "❄️", "autumn": "🍂", "petal": "🌸", "stem": "🌿",
    "thorn": "🌹", "bud": "🌷", "pollen": "🌼", "nectar": "🍯",
    "honeycomb": "🍯", "nest": "🪹", "feather": "🪶", "wing": "🪽",
    "burrow": "🕳️", "herd": "🐄", "oak": "🌳", "pine": "🌲",
    "maple": "🍁", "willow": "🌳", "banyan": "🌳", "neem": "🌿",
    "mangrove": "🌳", "orchid": "🌺", "jasmine": "🌼", "marigold": "🌻",
    "plant": "🌱", "springtime": "🌸",

    # --- Things / toys / music -------------------------------------------
    "toy": "🧸", "doll": "🪆", "clock": "🕐", "watch": "⌚",
    "lock": "🔒", "bag": "🎒", "box": "📦", "rope": "🪢",
    "string": "🧵", "balloon": "🎈", "bubble": "🫧", "candle": "🕯️",
    "lamp": "💡", "torch": "🔦", "mirror": "🪞", "brush": "🖌️",
    "comb": "🪮", "soap": "🧼", "towel": "🧻", "umbrella": "☂️",
    "cap": "🧢", "sock": "🧦", "shirt": "👕", "dress": "👗",
    "skirt": "👗", "coat": "🧥", "scarf": "🧣", "glove": "🧤",
    "button": "🔘", "pocket": "👖", "ring": "💍", "crown": "👑",
    "camera": "📷", "phone": "📱", "radio": "📻", "television": "📺",
    "computer": "💻", "robot": "🤖", "magnet": "🧲", "battery": "🔋",
    "wheel": "🎡", "puzzle": "🧩", "swing": "🛝", "slide": "🛝",
    "seesaw": "🛝", "marble": "🔮", "blocks": "🧱", "teddy": "🧸",
    "whistle": "📯", "flute": "🪈", "guitar": "🎸", "piano": "🎹",
    "violin": "🎻", "trumpet": "🎺", "basket": "🧺", "bucket": "🪣",
    "jar": "🫙", "bottle": "🍾", "can": "🥫", "tray": "🍽️",
    "coin": "🪙", "money": "💰", "ticket": "🎫", "map": "🗺️",
    "flag": "🚩", "gift": "🎁", "card": "💌", "needle": "🪡",
    "thread": "🧵", "scissors": "✂️", "glue": "🩹", "tape": "📼",
    "paper": "📄", "knot": "🪢", "chain": "⛓️", "hammer": "🔨",
    "nail": "🔩", "saw": "🪚", "ladder": "🪜", "broom": "🧹",
    "mop": "🧽", "sponge": "🧽", "list": "📋", "cushion": "🛋️",
    "blanket": "🛏️", "pillow": "🛏️", "curtain": "🪟", "carpet": "🧶",
    "basketball": "🏀", "racket": "🏓", "skate": "🛼", "helmet": "⛑️",
    "musicclass": "🎵", "picture": "🖼️", "drawing": "✏️",
    "painting": "🎨", "craft": "✂️",

    # --- Body / feelings --------------------------------------------------
    "eye": "👁️", "ear": "👂", "nose": "👃", "mouth": "👄",
    "hand": "✋", "foot": "🦶", "arm": "💪", "leg": "🦵",
    "head": "🧑", "hair": "💇", "face": "😊", "neck": "🧣",
    "back": "🔙", "chest": "🫁", "tummy": "🤰", "knee": "🦵",
    "elbow": "💪", "shoulder": "💪", "finger": "👆", "thumb": "👍",
    "toe": "🦶", "fingernail": "💅", "skin": "🧴", "bone": "🦴",
    "tooth": "🦷", "tongue": "👅", "lip": "👄", "chin": "🧑",
    "cheek": "😊", "forehead": "🧑", "eyebrow": "🤨", "eyelash": "👁️",
    "heartbeat": "💓", "brain": "🧠", "lung": "🫁", "blood": "🩸",
    "muscle": "💪", "wrist": "⌚", "ankle": "🦶", "heel": "👠",
    "palmhand": "🤚", "fist": "✊", "waist": "👖", "hip": "🕺",
    "smile": "😊", "laugh": "😄", "yawn": "🥱", "sneeze": "🤧",
    "breath": "😮‍💨", "voice": "🗣️", "whisper": "🤫", "shout": "📢",
    "blink": "😉", "wink": "😉", "nod": "🙂", "clap": "👏",
    "handwave": "👋", "point": "👆", "hug": "🤗", "jump": "🤸",
    "run": "🏃", "walk": "🚶", "skip": "🤸", "crawl": "🧎",
    "climb": "🧗", "stretch": "🤸", "bend": "🙇", "sit": "🪑",
    "stand": "🧍", "sleep": "😴", "dream": "💭", "wake": "⏰",
    "taste": "👅", "touch": "🤏", "smell": "👃", "hearing": "👂",
    "sight": "👀", "healthy": "💪", "tired": "😪", "hungry": "🍽️",
    "thirsty": "🥤", "happy": "😄", "sad": "😢", "angry": "😠",
    "scared": "😨", "brave": "🦁", "calm": "😌", "excited": "🤩",
    "proud": "😌", "shy": "😊", "kind": "🤗", "gentle": "🕊️",
    "strong": "💪", "quick": "⚡", "tall": "📏", "short": "📏",
    "warm": "🌡️", "cool": "❄️", "tickle": "😆",

    # --- Home -------------------------------------------------------------
    "door": "🚪", "window": "🪟", "roof": "🏠", "wall": "🧱",
    "floor": "🏠", "stairs": "🪜", "gate": "🚪", "fence": "🚧",
    "chair": "🪑", "table": "🪑", "bed": "🛏️", "sofa": "🛋️",
    "shelf": "📚", "cupboard": "🗄️", "drawer": "🗄️", "desk": "🪑",
    "kitchen": "🍳", "bedroom": "🛏️", "bathroom": "🛁", "garage": "🏠",
    "balcony": "🏠", "pot": "🍲", "pan": "🍳", "plate": "🍽️",
    "bowl": "🥣", "cup": "🥤", "glass": "🥛", "spoon": "🥄",
    "fork": "🍴", "knife": "🔪", "kettle": "🫖", "stove": "🍳",
    "oven": "🔥", "fridge": "🧊", "sink": "🚰", "tap": "🚰",
    "shower": "🚿", "bathtub": "🛁", "mat": "🧶", "rug": "🧶",
    "frame": "🖼️", "vase": "🏺", "candlestick": "🕯️", "switch": "💡",
    "plug": "🔌", "wire": "🔌", "fan": "🌀", "dustbin": "🗑️",
    "iron": "👔", "washer": "🧺", "hanger": "🧥", "bookshelf": "📚",
    "toolbox": "🧰", "hose": "🚿", "lawn": "🌱", "porch": "🏠",
    "chimney": "🏠", "attic": "🏠", "cellar": "🏠", "hall": "🚪",
    "corner": "📐", "ceiling": "🏠", "step": "🪜", "handle": "🚪",
    "hinge": "🚪", "bolt": "🔩", "letterbox": "📮", "doorbell": "🔔",
    "keyring": "🔑", "quilt": "🛏️", "sheet": "🛏️", "mattress": "🛏️",
    "cradle": "👶", "stool": "🪑", "bench": "🪑", "wardrobe": "🗄️",
    "lantern": "🏮", "bulb": "💡", "match": "🔥", "lid": "🍲",
    "jug": "🏺", "teapot": "🫖", "saucer": "🍽️", "napkin": "🧻",
    "apron": "🥻", "cloth": "🧵", "duster": "🧹", "scrubber": "🧽",
    "detergent": "🧴", "clothesline": "🧺",

    # --- Vehicles ---------------------------------------------------------
    "bus": "🚌", "train": "🚂", "plane": "✈️", "ship": "🚢",
    "bike": "🚲", "scooter": "🛵", "truck": "🚚", "van": "🚐",
    "jeep": "🚙", "taxi": "🚕", "tractor": "🚜", "digger": "🚜",
    "crane": "🏗️", "ambulance": "🚑", "firetruck": "🚒",
    "policecar": "🚓", "helicopter": "🚁", "submarine": "🤿",
    "canoe": "🛶", "kayak": "🛶", "raft": "🛶", "ferry": "⛴️",
    "sailboat": "⛵", "yacht": "🛥️", "tram": "🚊", "metro": "🚇",
    "monorail": "🚝", "trolley": "🛒", "wagon": "🛻", "cart": "🛒",
    "sledge": "🛷", "sleigh": "🛷", "skateboard": "🛹",
    "surfboard": "🏄", "glider": "🪂", "hotairballoon": "🎈",
    "parachute": "🪂", "jet": "🛩️", "engine": "⚙️", "tyre": "🛞",
    "brake": "🛑", "pedal": "🚲", "steering": "🎡", "seatbelt": "💺",
    "horn": "📢", "carmirror": "🪞", "headlight": "💡", "road": "🛣️",
    "street": "🛣️", "lane": "🛣️", "bridge": "🌉", "tunnel": "🕳️",
    "track": "🛤️", "station": "🚉", "airport": "🛫", "harbour": "⚓",
    "port": "⚓", "runway": "🛫", "parking": "🅿️", "signal": "🚦",
    "crossing": "🚸", "pavement": "🚶", "fuel": "⛽", "petrol": "⛽",
    "driver": "🧑", "pilot": "🧑‍✈️", "sailor": "⚓", "captain": "🧑‍✈️",
    "passenger": "🧍", "journey": "🗺️", "travel": "🧳",
    "wheelbarrow": "🛞", "rickshaw": "🛺", "caravan": "🚐",
    "lorry": "🚚", "tanker": "🚛", "mixer": "🚛", "bulldozer": "🚜",
    "forklift": "🚜", "combine": "🚜", "plough": "🚜",
    "spaceship": "🛸", "shuttle": "🚀", "satellite": "🛰️",
    "rover": "🛸", "seaplane": "🛩️", "speedboat": "🚤",
    "gondola": "🛶", "barge": "🚢", "trailer": "🚚", "moped": "🛵",
    "quadbike": "🏍️", "unicycle": "🚲", "tricycle": "🚲",
    "cablecar": "🚡",

    # --- School -----------------------------------------------------------
    "pen": "🖊️", "pencil": "✏️", "eraser": "🧽", "ruler": "📏",
    "sharpener": "✏️", "notebook": "📓", "board": "📋",
    "classroom": "🏫", "school": "🏫", "teacher": "🧑‍🏫",
    "student": "🧑‍🎓", "friend": "🧑‍🤝‍🧑", "lesson": "📖",
    "homework": "📝", "exam": "📝", "question": "❓", "answer": "✅",
    "story": "📖", "poem": "📜", "letterabc": "🔤", "alphabet": "🔤",
    "number": "🔢", "count": "🔢", "maths": "➗", "science": "🔬",
    "history": "📜", "library": "📚", "schoolbell": "🔔",
    "playground": "🛝", "break": "⏸️", "lunch": "🍱", "uniform": "👔",
    "satchel": "🎒", "crayons": "🖍️", "crayon": "🖍️",
    "gluestick": "🩹", "stapler": "📎", "paperclip": "📎",
    "folder": "📁", "chart": "📊", "globe": "🌍", "atlas": "🗺️",
    "dictionary": "📕", "page": "📄", "word": "🔤", "sentence": "📝",
    "spell": "🔤", "read": "📖", "write": "✍️", "learn": "🧠",
    "teach": "🧑‍🏫", "study": "📚", "think": "💭", "know": "💡",
    "practise": "🔁", "listen": "👂", "speak": "🗣️", "share": "🤝",
    "help": "🤝", "tidy": "🧹", "quiet": "🤫", "line": "📏",
    "group": "👥", "team": "👥", "game": "🎮", "prize": "🏆",
    "medal": "🏅", "goldstar": "⭐", "badge": "🎖️",
    "starchart": "📊", "report": "📋", "diary": "📔",
    "principal": "🧑‍💼", "office": "🏢", "corridor": "🚪",
    "canteen": "🍱", "assembly": "👥", "register": "📋",
    "timetable": "📅", "term": "📅", "holiday": "🏖️", "trip": "🚌",
    "project": "📊", "model": "🏗️", "experiment": "🧪",
    "microscope": "🔬", "magnifier": "🔍", "telescope": "🔭",
    "calculator": "🧮", "abacus": "🧮", "compass": "🧭",
    "protractor": "📐", "triangle": "📐", "square": "🟥",
    "circle": "⭕", "rectangle": "🟨", "oval": "🥚",

    # --- Colors -----------------------------------------------------------
    "yellow": "💛", "purple": "💜", "pink": "🩷", "brown": "🤎",
    "black": "🖤", "white": "🤍", "grey": "🩶", "gold": "🟡",
    "silver": "⚪", "ivory": "🤍", "beige": "🟤", "tan": "🟤",
    "bronze": "🟠", "copper": "🟠", "ruby": "❤️", "emerald": "💚",
    "sapphire": "💙", "amber": "🟠", "mint": "🟢", "teal": "🩵",
    "navy": "🔵", "skyblue": "🩵", "aqua": "🩵", "turquoise": "🩵",
    "indigo": "🔵", "violet": "💜", "lavender": "💜", "lilac": "💜",
    "magenta": "💗", "maroon": "🟥", "scarlet": "🔴", "crimson": "🔴",
    "rosepink": "🌸", "blush": "🌸", "salmon": "🧡", "mustard": "💛",
    "charcoal": "⚫", "slate": "🩶", "pearl": "🤍", "midnight": "🌃",
    "red": "🔴", "blue": "🔵", "green": "🟢", "bell": "🔔",
    "language": "🌐",
    "rainbow": "🌈", "color": "🎨", "bright": "☀️", "dark": "🌑",
    "pale": "🤍", "deep": "🟦", "shiny": "✨", "dull": "🩶",
    "glow": "💡", "sparkle": "✨", "shade": "🌑", "tint": "🎨",
    "stripe": "🦓", "spot": "🐆", "patch": "🩹", "swirl": "🌀",
    "check": "🏁", "plain": "⬜", "paint": "🎨", "marker": "🖊️",
    "palette": "🎨", "canvas": "🖼️", "dye": "🎨", "ink": "🖋️",
    "chalk": "🖍️", "pastel": "🎨", "sandy": "🏖️", "snowy": "❄️",
    "sunshine": "☀️", "seagreen": "🌊", "leafy": "🍃", "grassy": "🌱",
    "cocoa": "🤎", "caramel": "🍮", "toffee": "🍬", "cloudy": "☁️",
    "stormy": "⛈️", "misty": "🌫️", "dusky": "🌆", "fiery": "🔥",
    "icy": "🧊", "frosty": "❄️", "blossom": "🌸",
    "forestgreen": "🌲", "sunny": "☀️",

    # --- Weather ----------------------------------------------------------
    "wind": "💨", "storm": "⛈️", "thunder": "⛈️", "lightning": "⚡",
    "hail": "🌨️", "fog": "🌫️", "mist": "🌫️", "dew": "💧",
    "frost": "❄️", "ice": "🧊", "sleet": "🌨️", "drizzle": "🌦️",
    "rainshower": "🌦️", "puddle": "💧", "heat": "🌡️", "cold": "🥶",
    "chill": "🥶", "breeze": "🍃", "gale": "💨", "gust": "💨",
    "sunbeam": "🌞", "sunlight": "☀️", "moonlight": "🌙",
    "starlight": "✨", "daytime": "🌞", "nighttime": "🌜",
    "morning": "🌅", "noon": "🌞", "evening": "🌆", "dawn": "🌅",
    "dusk": "🌆", "twilight": "🌆", "seasons": "🍂",
    "monsoon": "🌧️", "drought": "🏜️", "flood": "🌊",
    "raincoat": "🧥", "boots": "🥾", "snowman": "⛄",
    "snowflake": "❄️", "icicle": "🧊", "blizzard": "🌨️",
    "avalanche": "🏔️", "cyclone": "🌀", "hurricane": "🌀",
    "tornado": "🌪️", "whirlwind": "🌀", "sandstorm": "🏜️",
    "humid": "💧", "damp": "💧", "dry": "🏜️", "wet": "💧",
    "soggy": "💧", "slippery": "⚠️", "muddy": "🟤", "dusty": "💨",
    "breezy": "🍃", "windy": "💨", "rainy": "🌧️", "snowyday": "🌨️",
    "stormyday": "⛈️", "frostyday": "❄️", "mistyday": "🌫️",
    "foggy": "🌫️", "clearsky": "☀️", "weather": "🌤️",
    "climate": "🌍", "forecast": "📊", "temperature": "🌡️",
    "thermometer": "🌡️", "barometer": "🌡️", "windvane": "🧭",
    "windmill": "🌬️", "sundial": "🕐", "sunglasses": "🕶️",
    "sunhat": "👒", "sunscreen": "🧴", "shelter": "⛺",
    "bonfire": "🔥", "fireplace": "🔥", "sweater": "🧥",
    "mitten": "🧤", "earmuff": "🎧", "snowball": "⛄",
    "slush": "🌨️", "thaw": "💧", "melt": "💧", "freeze": "🧊",
    "seasonal": "🍂",
}


def _twemoji_filename(emoji: str) -> str:
    """Return the Twemoji filename stem for *emoji*, e.g. ``"1f431"`` for 🐱.

    Twemoji names each asset by its Unicode code points, lower-case hex, joined
    with ``-``. Variation selectors (U+FE0F) are stripped, matching Twemoji's
    own naming (e.g. ☀️ -> ``2600`` not ``2600-fe0f``).
    """
    points = [f"{ord(ch):x}" for ch in emoji if ch != "️"]
    return "-".join(points)


def emoji_for(image_id_or_word: str) -> str:
    """Return the standard emoji character for *image_id_or_word*.

    Falls back to a sparkle when no emoji is mapped for the word.
    """
    key = (image_id_or_word or "").strip().lower()
    return _EMOJI.get(key, _FALLBACK_EMOJI)


def image_url_for(image_id_or_word: str) -> str:
    """Return a real emoji PNG image URL illustrating *image_id_or_word*.

    The argument may be an explicit illustration id (e.g. ``"cat"``) or a raw
    word. It is mapped to a standard emoji and then to the corresponding
    Twemoji PNG asset URL. Words without a known emoji use a friendly sparkle.
    """
    emoji = emoji_for(image_id_or_word)
    return f"{_TWEMOJI_BASE}{_twemoji_filename(emoji)}.png"


def available_ids() -> list[str]:
    """Return the sorted list of ids that have a dedicated emoji image."""
    return sorted(_EMOJI)
