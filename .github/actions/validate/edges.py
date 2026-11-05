"""Warns about black or white bars that were left around a background image."""
import os
import sys

from PIL import Image

DARK, LIGHT = 24, 232


def line(img, side, index):
    width, height = img.size
    if side == 'left':
        box = (index, 0, index + 1, height)
    elif side == 'right':
        box = (width - 1 - index, 0, width - index, height)
    elif side == 'top':
        box = (0, index, width, index + 1)
    else:
        box = (0, height - 1 - index, width, height - index)
    return img.crop(box)


def bar(img, side, size):
    """Returns (color, thickness, jump) of a solid bar at this edge, or None."""
    color, thickness = None, 0
    while thickness < size // 3:
        current = line(img, side, thickness)
        if current.getchannel('A').getextrema()[0] < 255:
            break
        luminance = current.convert('L').tobytes()
        dark = sum(value <= DARK for value in luminance) / len(luminance)
        light = sum(value >= LIGHT for value in luminance) / len(luminance)
        found = 'black' if dark >= 0.95 else 'white' if light >= 0.95 else None
        if not found or color not in (None, found):
            break
        color, thickness = found, thickness + 1

    if not color or thickness >= size // 3:
        return None

    # A pasted bar ends abruptly, a vignette or a dark scene fades out
    before = line(img, side, thickness - 1).convert('L').tobytes()
    after = line(img, side, min(thickness + 2, size - 1)).convert('L').tobytes()
    jump = sum(abs(a - b) >= 40 for a, b in zip(before, after)) / len(before)
    return color, thickness, jump


def find_bars(path):
    img = Image.open(path).convert('RGBA')
    width, height = img.size
    found = []
    for first, second, size in (('left', 'right', width), ('top', 'bottom', height)):
        bar_a, bar_b = bar(img, first, size), bar(img, second, size)
        if not bar_a or not bar_b or bar_a[0] != bar_b[0]:
            continue
        (color, thickness_a, jump_a), (_, thickness_b, jump_b) = bar_a, bar_b
        if min(thickness_a, thickness_b) < max(2, size * 0.008):
            continue
        if abs(thickness_a - thickness_b) > max(3, 0.25 * max(thickness_a, thickness_b)):
            continue
        if min(jump_a, jump_b) < 0.5:
            continue
        found.append(f'{color} bars on the {first} and {second} ({thickness_a}px and {thickness_b}px)')
    return found


def main():
    github = bool(os.getenv('GITHUB_ACTIONS'))
    for path in sys.argv[1:]:
        try:
            results = find_bars(path)
        except Exception as e:
            print(f'Could not check {path} for bars: {e}')
            continue
        for result in results:
            message = f'The background seems to have {result}. Please use the plain screenshot without bars'
            print(f'::warning file={path}::{message}' if github else f'warning: {path}: {message}')


if __name__ == '__main__':
    main()
