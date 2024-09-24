class Weight:
    __degree = 1
    __main_units = "г"
    __units = {
        __main_units: (10 ** 0) ** __degree,
        f"да{__main_units}": (10 ** 1) ** __degree,
        f"г{__main_units}": (10 ** 2) ** __degree,
        f"к{__main_units}": (10 ** 3) ** __degree,
        f"М{__main_units}": (10 ** 6) ** __degree,
        f"т": (10 ** 6) ** __degree,
        f"Г{__main_units}": (10 ** 9) ** __degree,
        f"Т{__main_units}": (10 ** 12) ** __degree,
        f"П{__main_units}": (10 ** 15) ** __degree,
        f"Э{__main_units}": (10 ** 18) ** __degree,
        f"З{__main_units}": (10 ** 21) ** __degree,
        f"И{__main_units}": (10 ** 24) ** __degree,
        f"д{__main_units}": (10 ** -1) ** __degree,
        f"с{__main_units}": (10 ** -2) ** __degree,
        f"м{__main_units}": (10 ** -3) ** __degree,
        f"мк{__main_units}": (10 ** -6) ** __degree,
        f"н{__main_units}": (10 ** -9) ** __degree,
        f"п{__main_units}": (10 ** -12) ** __degree,
        f"ф{__main_units}": (10 ** -15) ** __degree,
        f"а{__main_units}": (10 ** -18) ** __degree,
        f"з{__main_units}": (10 ** -21) ** __degree,
        f"и{__main_units}": (10 ** -24) ** __degree,
    }
    __units2 = {
        (10 ** 0) ** __degree: f"{__main_units}",
        (10 ** 1) ** __degree: f"да{__main_units}",
        (10 ** 2) ** __degree: f"г{__main_units}",
        (10 ** 3) ** __degree: f"к{__main_units}",
        (10 ** 6) ** __degree: f"М{__main_units}", (10 ** 6) ** __degree: f"т",
        (10 ** 9) ** __degree: f"Г{__main_units}",
        (10 ** 12) ** __degree: f"Т{__main_units}",
        (10 ** 15) ** __degree: f"П{__main_units}",
        (10 ** 18) ** __degree: f"Э{__main_units}",
        (10 ** 21) ** __degree: f"З{__main_units}",
        (10 ** 24) ** __degree: f"И{__main_units}",
        (10 ** -1) ** __degree: f"д{__main_units}",
        (10 ** -2) ** __degree: f"с{__main_units}",
        (10 ** -3) ** __degree: f"м{__main_units}",
        (10 ** -6) ** __degree: f"мк{__main_units}",
        (10 ** -9) ** __degree: f"н{__main_units}",
        (10 ** -12) ** __degree: f"п{__main_units}",
        (10 ** -15) ** __degree: f"ф{__main_units}",
        (10 ** -18) ** __degree: f"а{__main_units}",
        (10 ** -21) ** __degree: f"з{__main_units}",
        (10 ** -24) ** __degree: f"и{__main_units}"
    }

    def __init__(self, weight: str):
        import re
        weight = re.fullmatch(r'\s*[+-]?(?P<number>\d+[.]?\d*)\s*(?P<unit>\w+)\s*', weight.replace(",", "."))
        if not weight or not weight.group("number").replace(".", "").isnumeric() or \
                not self.__units.get(weight.group("unit")):
            raise ValueError("Weight is not correct")
        self.__unit = self.__units[weight.group("unit")]
        self.__number = \
            int(weight.group("number")) if weight.group("number").isnumeric() else float(weight.group("number"))

    def get_mass(self, unit_of_mass: str = None):
        if unit_of_mass is None:
            unit = self.__unit
        else:
            unit = self.__units[unit_of_mass]

        result = self.__number * (self.__unit / unit)
        result = int(result) if int(result) == result else result
        return result

    def __str__(self):
        return f"{self.__number}{self.__units2[self.__unit]}"

    def __repr__(self):
        return f"{self.__number}{self.__units2[self.__unit]}"


class Volume:
    __degree = 3
    __main_units = "м³"
    __units = {
        __main_units: (10 ** 0) ** __degree,
        f"да{__main_units}": (10 ** 1) ** __degree,
        f"г{__main_units}": (10 ** 2) ** __degree,
        f"к{__main_units}": (10 ** 3) ** __degree,
        f"М{__main_units}": (10 ** 6) ** __degree,
        f"Г{__main_units}": (10 ** 9) ** __degree,
        f"Т{__main_units}": (10 ** 12) ** __degree,
        f"П{__main_units}": (10 ** 15) ** __degree,
        f"Э{__main_units}": (10 ** 18) ** __degree,
        f"З{__main_units}": (10 ** 21) ** __degree,
        f"И{__main_units}": (10 ** 24) ** __degree,
        f"д{__main_units}": (10 ** -1) ** __degree, f"л": (10 ** -1) ** __degree,
        f"с{__main_units}": (10 ** -2) ** __degree, f"мл": (10 ** -2) ** __degree,
        f"м{__main_units}": (10 ** -3) ** __degree,
        f"мк{__main_units}": (10 ** -6) ** __degree,
        f"н{__main_units}": (10 ** -9) ** __degree,
        f"п{__main_units}": (10 ** -12) ** __degree,
        f"ф{__main_units}": (10 ** -15) ** __degree,
        f"а{__main_units}": (10 ** -18) ** __degree,
        f"з{__main_units}": (10 ** -21) ** __degree,
        f"и{__main_units}": (10 ** -24) ** __degree,
    }
    __units2 = {
        (10 ** 0) ** __degree: f"{__main_units}",
        (10 ** 1) ** __degree: f"да{__main_units}",
        (10 ** 2) ** __degree: f"г{__main_units}",
        (10 ** 3) ** __degree: f"к{__main_units}",
        (10 ** 6) ** __degree: f"М{__main_units}",
        (10 ** 9) ** __degree: f"Г{__main_units}",
        (10 ** 12) ** __degree: f"Т{__main_units}",
        (10 ** 15) ** __degree: f"П{__main_units}",
        (10 ** 18) ** __degree: f"Э{__main_units}",
        (10 ** 21) ** __degree: f"З{__main_units}",
        (10 ** 24) ** __degree: f"И{__main_units}",
        (10 ** -1) ** __degree: f"д{__main_units}", (10 ** -1) ** __degree: f"л",
        (10 ** -2) ** __degree: f"с{__main_units}", (10 ** -2) ** __degree: f"мл",
        (10 ** -3) ** __degree: f"м{__main_units}",
        (10 ** -6) ** __degree: f"мк{__main_units}",
        (10 ** -9) ** __degree: f"н{__main_units}",
        (10 ** -12) ** __degree: f"п{__main_units}",
        (10 ** -15) ** __degree: f"ф{__main_units}",
        (10 ** -18) ** __degree: f"а{__main_units}",
        (10 ** -21) ** __degree: f"з{__main_units}",
        (10 ** -24) ** __degree: f"и{__main_units}"
    }

    def __init__(self, volume: str):
        import re
        volume = re.fullmatch(r'\s*[+-]?(?P<number>\d+[.]?\d*)\s*(?P<unit>\w+)\s*', volume.replace(",", "."))
        if not volume or not volume.group("number").replace(".", "").isnumeric() or \
                not self.__units.get(volume.group("unit")):
            raise ValueError("Volume is not correct")
        self.__unit = self.__units[volume.group("unit")]
        self.__number = \
            int(volume.group("number")) if volume.group("number").isnumeric() else float(volume.group("number"))

    def get_volume(self, unit_of_mass: str = None):
        if unit_of_mass is None:
            unit = self.__unit
        else:
            unit = self.__units[unit_of_mass]

        result = self.__number * (self.__unit / unit)
        result = int(result) if int(result) == result else result
        return result

    def __str__(self):
        return f"{self.__number}{self.__units2[self.__unit]}"

    def __repr__(self):
        return f"{self.__number}{self.__units2[self.__unit]}"


def round(number):
    import math
    result = math.floor(number * 10 ** 5 + 0.5) / 10 ** 5
    return int(result) if int(result) == result else result
