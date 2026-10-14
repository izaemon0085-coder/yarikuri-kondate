from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
SCALE = 4
FOLDER = Path(__file__).parent / "images"


def canvas(background):
    image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse(s(16, 16, 496, 496), fill=background)
    return image, draw


def s(*values):
    return [value * SCALE for value in values]


def save(image, name):
    FOLDER.mkdir(exist_ok=True)
    image.resize((SIZE, SIZE), Image.LANCZOS).save(FOLDER / name)


def paw():
    image, draw = canvas("#FFE3EA")
    pink = "#EC7A9C"
    draw.ellipse(s(146, 238, 366, 418), fill=pink)
    for x, y in [(104, 168), (178, 110), (262, 110), (336, 168)]:
        draw.ellipse(s(x, y, x + 72, y + 92), fill=pink)
    save(image, "logo_nikukyu.png")


def bowl():
    image, draw = canvas("#FFF1D9")
    draw.line(s(300, 96, 420, 196), fill="#9C6B43", width=18 * SCALE)
    draw.line(s(330, 84, 440, 172), fill="#9C6B43", width=18 * SCALE)
    draw.ellipse(s(126, 150, 386, 330), fill="white", outline="#E9E1D6", width=4 * SCALE)
    draw.chord(s(96, 150, 416, 430), start=0, end=180, fill="#E35D5B")
    draw.rectangle(s(96, 286, 416, 292), fill="#E35D5B")
    draw.rounded_rectangle(s(206, 420, 306, 444), radius=10 * SCALE, fill="#C94B49")
    draw.ellipse(s(150, 330, 176, 356), fill="#F5A3A1")
    draw.ellipse(s(336, 330, 362, 356), fill="#F5A3A1")
    save(image, "logo_ochawan.png")


def basket():
    image, draw = canvas("#E2F4E6")
    draw.arc(s(150, 110, 362, 330), start=180, end=360, fill="#A86F3E", width=20 * SCALE)
    draw.polygon(s(250, 230, 216, 120, 236, 116, 262, 226), fill="#F08A3C")
    draw.ellipse(s(196, 84, 236, 132), fill="#5DAA5B")
    draw.ellipse(s(222, 76, 262, 124), fill="#6CBF69")
    draw.ellipse(s(282, 170, 352, 240), fill="#E35D5B")
    draw.ellipse(s(306, 156, 326, 176), fill="#5DAA5B")
    draw.polygon(s(110, 224, 402, 224, 362, 410, 150, 410), fill="#D9A066")
    for y in (270, 320, 370):
        draw.line(s(122, y, 390, y), fill="#B9824C", width=8 * SCALE)
    draw.rounded_rectangle(s(96, 210, 416, 240), radius=12 * SCALE, fill="#B9824C")
    save(image, "logo_kago.png")


def cat():
    image, draw = canvas("#FFF0D6")
    orange = "#F4A259"
    draw.polygon(s(136, 220, 150, 100, 236, 170), fill=orange)
    draw.polygon(s(376, 220, 362, 100, 276, 170), fill=orange)
    draw.polygon(s(158, 196, 164, 132, 214, 172), fill="#F7C6CF")
    draw.polygon(s(354, 196, 348, 132, 298, 172), fill="#F7C6CF")
    draw.ellipse(s(116, 146, 396, 406), fill=orange)
    draw.ellipse(s(196, 236, 230, 280), fill="#4A3B35")
    draw.ellipse(s(282, 236, 316, 280), fill="#4A3B35")
    draw.ellipse(s(206, 244, 218, 258), fill="white")
    draw.ellipse(s(292, 244, 304, 258), fill="white")
    draw.polygon(s(242, 296, 270, 296, 256, 312), fill="#EC7A9C")
    draw.arc(s(226, 300, 258, 332), start=20, end=160, fill="#4A3B35", width=5 * SCALE)
    draw.arc(s(254, 300, 286, 332), start=20, end=160, fill="#4A3B35", width=5 * SCALE)
    for y in (300, 324):
        draw.line(s(120, y - 10, 196, y), fill="#4A3B35", width=4 * SCALE)
        draw.line(s(392, y - 10, 316, y), fill="#4A3B35", width=4 * SCALE)
    draw.ellipse(s(160, 300, 196, 324), fill="#F7B7A3")
    draw.ellipse(s(316, 300, 352, 324), fill="#F7B7A3")
    save(image, "logo_neko.png")


paw()
bowl()
basket()
cat()
print("saved:", sorted(path.name for path in FOLDER.glob("*.png")))