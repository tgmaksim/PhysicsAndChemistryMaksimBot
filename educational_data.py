import re
import math
import itertools
from typing import Union, Literal
from chemlib import Reaction, Compound
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from core import resources_path, except_calculate
from physical_quantities import Volume, round, Weight
from aiogram.types import (
    Message,
    FSInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


class DataPath:
    def __init__(self, *path: str):
        self._path = path

    @property
    def data(self) -> Union['EducationalData', 'EducationalInformation', 'EducationalFunction', None]:
        data = functions
        for i in self._path:
            data = data.__getitem__(i)
        return data

    @property
    def parent(self) -> Union['DataPath', None]:
        return DataPath(*self._path[:-1]) if len(self._path) > 1 else DataPath()

    @property
    def path(self) -> str:
        return ".".join(self._path) if self._path else "stop"

    def __bool__(self) -> bool:
        return bool(self._path)


markdown: Literal['Markdown'] = "Markdown"
html: Literal['HTML'] = "HTML"


class DataEducationalInformation:
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data

    def __bool__(self) -> bool:
        return bool(self._data)


class TextEducationalInformation(DataEducationalInformation):
    def __init__(self, text: str, parse_mode: Literal['Markdown', 'HTML'] = markdown):
        super().__init__(text)
        self._parse_mode = parse_mode

    @property
    def parse_mode(self) -> str:
        return self._parse_mode

    async def __call__(self, message: Message, data_path: DataPath):
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="<<<Назад", callback_data=data_path.parent.path)]])
        await message.edit_text(self.data, parse_mode=self._parse_mode, reply_markup=markup)


class PhotoEducationalInformation(DataEducationalInformation):
    def __init__(self, path: str, text: TextEducationalInformation = TextEducationalInformation('')):
        super().__init__(FSInputFile(resources_path(path)))
        self._text = text

    async def __call__(self, message: Message, data_path: DataPath):
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="<<<Назад", callback_data="_del" + data_path.parent.path)]])
        await message.delete()
        await message.answer_photo(self.data, self._text.data, parse_mode=self._text.parse_mode, reply_markup=markup)


class EducationalInformation:
    def __init__(self, text: str, inf: Union[TextEducationalInformation, str, PhotoEducationalInformation]):
        self._data_path = DataPath()
        self._text = text
        self._inf = inf if not isinstance(inf, str) else Text(inf)

    @property
    def data_path(self) -> DataPath:
        return self._data_path

    @data_path.setter
    def data_path(self, value: DataPath) -> None:
        self._data_path = value

    @property
    def inline_keyboard_button(self) -> 'InlineKeyboardButton':
        return InlineKeyboardButton(
            text=self._text,
            callback_data=self._data_path.path
        )

    async def __call__(self, message, _=None):
        await self._inf(message, self._data_path)


class EducationalData:
    def __init__(self, text: Union[str, None], data_path: DataPath, buttons_row: int = 2,
                 **datas: Union['EducationalData', 'EducationalInformation', 'EducationalFunction']):
        self._text = text
        self._data_path = data_path
        self._button_row = buttons_row
        self._datas = {}
        if not isinstance(self, BackEducationalData):
            self._datas['back'] = BackEducationalData(self._data_path.parent)
        self._datas.update(**datas)
        for i in self._datas:
            if isinstance(self._datas[i], EducationalInformation):
                self._datas[i].data_path = DataPath(*(self._data_path.path.split(".") + [i]))

    def __getitem__(self, item: str) -> Union['EducationalData', 'EducationalInformation', 'EducationalFunction']:
        return self._datas[item]

    @property
    def inline_keyboard_buttons(self) -> list[list['InlineKeyboardButton']]:
        buttons = [child.inline_keyboard_button for child in self._datas.values()]
        result = [[buttons[0]]]
        for i in range(1, len(buttons), self._button_row):
            result.append(buttons[i: min(len(buttons), i + self._button_row)])
        return result

    @property
    def inline_keyboard_button(self) -> 'InlineKeyboardButton':
        return InlineKeyboardButton(
            text=self._text,
            callback_data=self._data_path.path
        )

    async def __call__(self, message: Message, new: bool = False):
        markup = InlineKeyboardMarkup(inline_keyboard=self.inline_keyboard_buttons)
        if new:
            await message.answer("Выберите раздел или понятие", reply_markup=markup)
        else:
            await message.edit_text("Выберите раздел или понятие", reply_markup=markup)


class BackEducationalData(EducationalData):
    def __init__(self, data_path: DataPath):
        super().__init__(
            text="Назад",
            data_path=data_path
        )


class ResultCalculate:
    def __init__(self, answer: str, result: Union[str, int, float]):
        self._answer = answer
        self._result = result

    def __iter__(self):
        self._i = 0
        return self

    def __next__(self):
        x = self._i
        self._i += 1
        if self._i > 2:
            raise StopIteration()
        return [self._answer, self._result][x]

    @property
    def answer(self) -> str:
        return self._answer

    @property
    def result(self) -> Union[str, int]:
        return self._result


# Класс нужен для определения состояния пользователя в данном боте,
# например: пользователь должен отправить отзыв в следующем сообщении
class UserState(StatesGroup):
    review = State('review')

    molecular_weight = State('molecular_weight')
    mass_fraction1 = State('mass_fraction1')
    mass_fraction2 = State('mass_fraction2')
    volume_fraction1 = State('volume_fraction1')
    volume_fraction2 = State('volume_fraction2')
    amount_of_substance_from_mass1 = State('amount_of_substance_from_mass1')
    amount_of_substance_from_mass2 = State('amount_of_substance_from_mass2')
    amount_of_substance_from_number_of_particles = State('amount_of_substance_from_number_of_particles')
    amount_of_substance_from_volume_of_gas = State('amount_of_substance_from_volume_of_gas')
    gas_density = State('gas_density')

    formulation_of_chemical_formulas = State('formulation_of_chemical_formulas')
    making_formulas_by_name = State('making_formulas_by_name')
    setting_coefficients = State('setting_coefficients')


class calculate_chemistry:
    @staticmethod
    @except_calculate
    async def molecular_weight(message: Message, _):
        await message.answer(molecular_weight(message.text, get_elements(message.text)).answer, parse_mode=html)
        await functions['calculate_chemistry']['molecular_weight'].function(message)

    @staticmethod
    @except_calculate
    async def mass_fraction1(message: Message, state: FSMContext):
        elements = get_elements(message.text)
        await state.update_data(elements=elements, string=message.text)
        await state.set_state(UserState.mass_fraction2)
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=element, callback_data=element)] for element in set(elements)])
        await message.answer("Выберите элемент", reply_markup=markup)

    @staticmethod
    async def mass_fraction2(callback_query: CallbackQuery, state: FSMContext):
        elements = (await state.get_data())['elements']
        string = (await state.get_data())['string']
        await state.clear()
        await state.set_state(UserState.mass_fraction1)
        await callback_query.message.edit_text(mass_fraction(string, callback_query.data, elements).answer,
                                               parse_mode=html)
        await functions['calculate_chemistry']['mass_fraction'].function(callback_query.message)

    @staticmethod
    @except_calculate
    async def volume_fraction1(message: Message, state: FSMContext):
        Volume(message.text)
        await state.update_data(volume_mixture=message.text)
        await state.set_state(UserState.volume_fraction2)
        await message.answer("Отправьте объем нужного Вам вещества в этой смеси с указанием единиц "
                             "измерения. Например: `3л` или `3м³`", parse_mode=markdown)

    @staticmethod
    @except_calculate
    async def volume_fraction2(message: Message, state: FSMContext):
        volume_mixture = (await state.get_data())['volume_mixture']
        await state.clear()
        await state.set_state(UserState.volume_fraction1)
        await message.answer(volume_fraction(message.text, volume_mixture).answer, parse_mode=html)
        await functions['calculate_chemistry']['volume_fraction'].function(message)

    @staticmethod
    @except_calculate
    async def amount_of_substance_from_mass1(message: Message, state: FSMContext):
        Weight(message.text.replace(",", "."))
        await state.update_data(weight=message.text.replace(",", "."))
        await state.set_state(UserState.amount_of_substance_from_mass2)
        await message.answer("Отправьте мне формулу вещества, для которого нужно посчитать количество вещества")

    @staticmethod
    @except_calculate
    async def amount_of_substance_from_mass2(message: Message, state: FSMContext):
        weight = (await state.get_data())['weight']
        await state.clear()
        await state.set_state(UserState.amount_of_substance_from_mass1)
        await message.answer(amount_of_substance_from_mass(weight, message.text).answer, parse_mode=html)
        await functions['calculate_chemistry']['amount_of_substance_from_mass'].function(message)

    @staticmethod
    @except_calculate
    async def amount_of_substance_from_number_of_particles(message: Message, _):
        await message.answer(amount_of_substance_from_number_of_particles(message.text).answer, parse_mode=html)
        await functions['calculate_chemistry']['amount_of_substance_from_number_of_particles'].function(message)

    @staticmethod
    @except_calculate
    async def amount_of_substance_from_volume_of_gas(message: Message, _):
        await message.answer(amount_of_substance_from_volume_of_gas(message.text).answer, parse_mode=html)
        await functions['calculate_chemistry']['amount_of_substance_from_volume_of_gas'].function(message)

    @staticmethod
    async def gas_density(message: Message, _):
        await message.answer(gas_density(message.text).answer, parse_mode=html)
        await functions['calculate_chemistry']['gas_density'].function(message)


class task_chemistry:
    @staticmethod
    @except_calculate
    async def formulation_of_chemical_formulas(message: Message, _):
        await message.answer(formulation_of_chemical_formulas(message.text), parse_mode=html)
        await functions['task_chemistry']['formulation_of_chemical_formulas'].function(message)

    @staticmethod
    @except_calculate
    async def making_formulas_by_name(message: Message, _):
        await message.answer(making_formulas_by_name(message.text), parse_mode=html)
        await functions['task_chemistry']['making_formulas_by_name'].function(message)

    @staticmethod
    @except_calculate
    async def setting_coefficients(message: Message, _):
        await message.answer(setting_coefficients(message.text), parse_mode=html)
        await functions['task_chemistry']['setting_coefficients'].function(message)


class EducationalFunction:
    def __init__(self, text: str, data_path: DataPath, state: State, function):
        self._text = text
        self._data_path = data_path
        self._state = state
        self._function = function

    async def __call__(self, message: Message, state: FSMContext):
        await state.set_state(self._state)
        await self._function(message)

    @property
    def function(self):
        return self._function

    @property
    def text(self) -> str:
        return self._text

    @property
    def inline_keyboard_button(self) -> 'InlineKeyboardButton':
        return InlineKeyboardButton(
            text=self._text,
            callback_data=self._data_path.path
        )


def setting_coefficients(string: str):
    if "=" not in string:
        return "Уравнение некорректно! Нет знака равно (=)"

    answer, type_reaction, suma = calculate_equation(string.replace("=", ">"))

    def build_number(text: str):
        for key in ["2", "3", "4", "5", "6", "7", "8", "9"]:
            text = text.replace(key, f"<b>{key}</b>")
        return text

    return f"{build_number(answer)}\n" \
           f"Тип реакции: <b>{type_reaction}</b>\n" \
           f"Сумма коэффициентов реакции: <b>{suma}</b>"


def calculate_equation(string: str):
    numbers_to_index = {"1": "", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈",
                        "9": "₉"}
    text = "".join(numbers_to_index.get(i, i) for i in string)
    list_reactants = [element.strip() for element in text.split(">")[0].split("+")]
    list_products = [element.strip() for element in text.split(">")[1].split("+")]

    reaction = Reaction.by_formula(text)
    reactants: list[Compound] = reaction.reactants
    products: list[Compound] = reaction.products

    if len(reactants) > 1 and len(products) == 1:
        type_reaction = "соединение"
    elif len(reactants) == 1 and len(products) > 1:
        type_reaction = "разложение"
    elif False not in [len(set_number) > 1 for set_number in [set([element.properties['AtomicNumber']
                                                                   for element in reactant.elements])
                                                              for reactant in reactants]] and \
            False not in [len(set_number) > 1 for set_number in [set([element.properties['AtomicNumber']
                                                                      for element in reactant.elements])
                                                                 for reactant in reactants]]:
        type_reaction = "обмен"
    else:
        type_reaction = "замещение"

    reaction.balance()

    coefficients = [str(number).replace("1", "") for number in list(reaction.coefficients.values())]
    list_reactants = [coefficients[i] + r for i, r in enumerate(list_reactants)]
    list_products = [coefficients[i + len(list_reactants)] + r for i, r in enumerate(list_products)]

    answer = " + ".join(list_reactants) + " = " + " + ".join(list_products)

    return answer, type_reaction, sum(list(reaction.coefficients.values()))


def making_formulas_by_name(string: str):
    element_to_simple_subs = \
        {"O": "1. O₂ - кислород\n2. O₃ - озон", "H": "1. H₂ - водород", "N": "1. N₂ - азот", "F": "1. F₂ - фтор"}
    name_sub_to_formula = \
        {"кислород": "O", "озон": "O", "водород": "H", "азот": "N", "фтор": "F", "хлороводород": "HCl",
         "сероводород": "HS", "бромистоводород": "HBr", "фтороводород": "HF", "иодоводород": "HI",
         "азотистоводород": "HN", "циановодород": "HCN"}
    compound_to_formula = \
        {"гидрид": "H", "борид": "B", "оксид": "O", "астатид": "At",
         "бромид": "Br", "сульфид": "S", "хлорид": "Cl", "фторид": "F", "иодид": "I", "карбид": "C", "нитрид": "N",
         "силицид": "Si", "фосфид": "P", "арсенид": "As", "селенид": "Se", "теллурид": "Te", "карбонат": "CO₃",
         "нитрат": "NO₃", "нитрит": "NO₂", "гидроксид": "OH", "фосфат": "PO₄", "ортофосфат": "PO₄", "метафосфат": "PO₃",
         "силикат": "SiO₃", "сульфит": "SO₃", "сульфат": "SO₄", "бромит": "BrO₂", "бромат": "BrO₃", "гипобромит": "BrO",
         "ванадат": "VO₃", "вольфрамат": "WO₄", "бериллат": "BeO₄", "дисульфат": "S₂O₇",
         "дифосфат": "P₂O₇", "пирофосфат": "P₂O₇", "дихромат": "Cr₂O₇", "периодат": "IO₄", "гипоиодит": "IO",
         "перманганат": "MnO₄", "метаборат": "BO₂", "борат": "BO₃", "хромат": "CrO₄", "цианид": "CN",
         "метаарсенит": "AsO₂", "ортоарсенит": "AsO₃", "арсенат": "AsO₄", "оксалат": "C₂O₄", "хлорит": "ClO₂",
         "хлорат": "ClO₃", "перохлорат": "ClO₄", "гипохлорит": "ClO", "гидрокарбонат": "HCO₃", "гидросульфат": "HSO₄",
         "гидросульфит": "HSO₃", "гидрофосфат": "HPO₄", "гидроортофосфат": "HPO₄", "азид": "N₃",
         "дигидрофосфат": "H₂PO₄", "дигидроортофосфат": "H₂PO₄", "фосфит": "HPO₃", "гипофосфит": "H₂PO₂"}
    genitive_elements2 = \
        {"водорода": "H", "лития": "Li", "бериллия": "Be", "бора": "B", "углерода": "C", "азота": "N", "кислорода": "O",
         "фтора": "F", "натрия": "Na", "магния": "Mg", "алюминия": "Al", "кремния": "Si", "фосфора": "P", "серы": "S",
         "хлора": "Cl", "калия": "K", "кальция": "Ca", "скандия": "Sc", "титана": "Ti", "вандия": "V", "хрома": "Cr",
         "марганца": "Mn", "железа": "Fe", "кобальта": "Co", "никеля": "Ni", "меди": "Cu", "цинка": "Zn", "галия": "Ga",
         "германия": "Ge", "мышьяка": "As", "селена": "Se", "брома": "Br", "рубидия": "Rb", "стронция": "Sr",
         "иттрия": "Y", "циркония": "Zr", "ниобия": "Nb", "молибдена": "Mo", "технеция": "Tc", "Рутения": "Ru",
         "родия": "Rh", "палладия": "Pd", "серебра": "Ag", "кадмия": "Cd", "индия": "In", "олова": "Sn", "сурьмы": "Sb",
         "теллура": "Te", "йода": "I", "цезия": "Cs", "бария": "Ba", "гафния": "Hf", "тантала": "Ta", "вольфрама": "W",
         "рения": "Re", "осмия": "Os", "иридия": "Ir", "платины": "Pt", "золота": "Au", "ртути": "Hg", "талия": "Tl",
         "свинца": "Pb", "висмута": "Bi", "полония": "Po", "астата": "At", "франция": "Fr", "радия": "Ra",
         "резерфордия": "Rf", "дубния": "Db", "сиборгия": "Sg", "бория": "Bh", "хассия": "Hs", "мейтнерия": "Mt",
         "дармштадтия": "Ds", "рентгения": "Rg", "коперниция": "Cn", "нихония": "Nh", "флеровия": "Fl",
         "московия": "Mc", "ливермория": "Lv", "теннессина": "Ts", "оганесона": "Og", "лантана": "La", "церия": "Ce",
         "празеодима": "Pr", "неодима": "Nd", "прометия": "Pm", "самария": "Sm", "европия": "Eu", "гадолиния": "Gd",
         "тербия": "Tb", "диспрозия": "Dy", "гольмия": "Ho", "эрбия": "Er", "тулия": "Tm", "иттербия": "Yb",
         "лютеция": "Lu", "актиния": "Ac", "тория": "Th", "протактиния": "Pa", "урана": "U", "нептуния": "Np",
         "плутония": "Pu", "америция": "Am", "кюрия": "Cm", "берклия": "Bk", "калифорния": "Cf", "эйнштейния": "Es",
         "фермия": "Fm", "менделевия": "Md", "нобелия": "No", "лоуренция": "Lr"}
    acid_to_formula = \
        {"хлороводородная": "HCl", "соляная": "HCl", "сероводородная": "HS", "сернистая": "HSO", "серная": "HSO",
         "азотистая": "HNO", "азотная": "HNO", "угольная": "HCO", "кремниевая": "HSiO", "бромоводородная": "HBr",
         "фтороводородная": "HF", "плавиковая": "HF", "иодоводородная": "HI", "азотистоводородная": "HN",
         "ортофосфорная": "HPO", "фосфорная": "HPO", "метафосфорная": "HPO", "бромистая": "HBrO",
         "бромноватая": "HBrO", "бромноватистая": "HBrO", "гипобромистая": "HBrO", "ванадиевая": "HVO",
         "вольфрамовая": "HWO", "дисерная": "HSO", "дифосфорная": "HPO", "пирофосфорная": "HPO",
         "дихромовая": "HCrO", "иодная": "HIO", "иодноватистая": "HIO", "марганцовая": "HMnO", "метаборная": "HBO",
         "метамышьяковистая": "HAsO", "ортоборная": "HBO", "борная": "HBO", "ортомышьяковистая": "HAsO",
         "ортомышьяковая": "HAsO", "хромовая": "HCrO", "хлористая": "HClO", "хлорная": "HClO",
         "хлорноватая": "HClO", "хлорноватистая": "HClO", "синильная": "HCN", "циановодородная": "HCN",
         "этандиовая": "HCO", "щавельная": "HCO"}
    _compound_to_formula = None
    if element_to_simple_subs.get(name_sub_to_formula.get(string.lower())):
        return element_to_simple_subs[name_sub_to_formula[string.lower()]]
    if name_sub_to_formula.get(string.lower()):
        text = name_sub_to_formula[string.lower()]
    else:
        text = string.lower().split(" ")
        if compound_to_formula.get(text[0]):
            _compound_to_formula = text[:]
            text = compound_to_formula[text[0]] + genitive_elements2[text[1]]
        elif compound_to_formula.get(text[1]):
            _compound_to_formula = text[::-1]
            text = compound_to_formula[text[1]] + genitive_elements2[text[0]]
        elif acid_to_formula.get(text[0]):
            text = acid_to_formula[text[0]]
        else:
            text = acid_to_formula[text[1]]
    answer = ""
    base_elements, del_element = get_base_element(text)
    elements = get_elements(text, True)
    [elements.remove(element) for element in get_elements(del_element, True)]
    if len(elements) != 1:
        return "К сожалению, я не могу посчитать индексы для этого вещества"
    i = 0
    for base_element in base_elements:
        answer += count_indexes([valence(element) for element in elements], list(elements), base_element, i)
        i = len(answer.split("\n")) // 2 - 1

    if _compound_to_formula is not None:
        answer = answer.split('\n')
        for i, string in enumerate(answer):
            if (re.fullmatch(fr"[\s\S]+\({_compound_to_formula[0]}\)[\s\S]+", string)
                or re.fullmatch(fr"[\s\S]+ {_compound_to_formula[0]} [\s\S]+", string)) and \
                    re.fullmatch(fr"[\s\S]+ {_compound_to_formula[1]}[\s\S]*", string):
                answer[i] = f"<b>{answer[i]}</b>"
        answer = "\n".join(answer)

    return answer


def formulation_of_chemical_formulas(string: str) -> str:
    element_to_simple_subs = \
        {"O": "1. O₂ - кислород\n2. O₃ - озон", "H": "1. H₂ - водород", "N": "1. N₂ - азот", "F": "1. F₂ - фтор"}
    if element_to_simple_subs.get(string):
        return element_to_simple_subs[string]
    answer = ""
    base_elements, del_element = get_base_element(string)
    elements = get_elements(string, True)
    [elements.remove(element) for element in get_elements(del_element, True)]
    if len(elements) != 1:
        return "К сожалению, я не могу посчитать индексы для этого вещества"
    i = 0
    for base_element in base_elements:
        answer += count_indexes([valence(element) for element in elements], list(elements), base_element, i)
        i = len(answer.split("\n")) // 2
    return answer


def count_indexes(valences_elements: list, elements: list, base: str, i: int = 0):
    valence_ions = \
        {"H": 1, "B": 3, "O": 2, "At": 1,
         "Br": 1, "S": 2, "Cl": 1, "F": 1, "I": 1, "C": 4, "N": 3, "Si": 4, "P": 3, "As": 3, "Se": 2, "Te": 2,
         "CO₃": 2, "NO₃": 1, "NO₂": 1, "OH": 1, "PO₄": 3, "PO₃": 1, "SiO₃": 2, "SO₃": 2, "SO₄": 2,
         "BrO₂": 1, "BrO₃": 1, "BrO": 1, "VO₃": 1, "WO₄": 2, "BeO₄": 2, "S₂O₇": 2, "P₂O₇": 4, "Cr₂O₇": 2,
         "IO₄": 1, "IO": 1, "MnO₄": 1, "BO₂": 1, "BO₃": 3, "CrO₄": 2, "CN": 1, "AsO₂": 1, "AsO₃": 3, "AsO₄": 3,
         "C₂O₄": 2, "ClO₂": 1, "ClO₃": 1, "ClO₄": 1, "ClO": 1, "HCO₃": 1, "HSO₄": 1, "HSO₃": 1, "HPO₄": 2, "H₂PO₄": 1,
         "HPO₃": 2, "H₂PO₂": 1, "N₃": 1}
    number_to_index = \
        {"1": "", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
    numbers_to_index = \
        {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
    valence_to_number = {1: "ₗ", 2: "ₗₗ", 3: "ₗₗₗ", 4: "ₗᵥ", 5: "ᵥ", 6: "ᵥₗ", 7: "ᵥₗₗ", 8: "ᵥₗₗₗ"}
    tabul = '\t'
    nti = lambda number: number_to_index[number] if int(number) < 10 \
        else "".join([numbers_to_index[n] for n in number])
    elements.append(base)
    list_elements = list(elements)
    elements2 = list(elements)
    answer = ""
    valence_base_element = [valence_ions.get(base)]
    if not valence_base_element[0]:
        valence_base_element = valence(base)
    valences_elements.append(valence_base_element)
    for valences in itertools.product(*valences_elements):
        lcm = get_lcm(*valences)
        coefficients = [int(lcm / i) for i in valences]
        for element in list_elements:
            if len(get_elements(list_elements[list_elements.index(element)], True)) > 1 or \
                    list_elements[list_elements.index(element)][-1] in numbers_to_index.values():
                add1, add2 = ("(", ")") if nti(str(coefficients[list_elements.index(element)])) else ("", "")
                elements[list_elements.index(element)] = \
                    f"{add1}{list_elements[list_elements.index(element)]}{add2}" \
                    f"{nti(str(coefficients[list_elements.index(element)]))}"
            else:
                elements[list_elements.index(element)] = list_elements[list_elements.index(element)] + \
                                                         nti(str(coefficients[list_elements.index(element)]))
        i += 1
        if i == 1: answer += "Ответ:\n"
        answer += f"{'  ' * (len(str(i)) + 2)}{tabul * (math.ceil(len(elements[0]) / 2))}" \
                  f"{valence_to_number[valences[0]]}" \
                  f"{tabul * (math.ceil(len(elements[0]) / 2))}" \
                  f"{tabul * (math.ceil(len(elements[1]) / 2 + 1))}" \
                  f"{valence_to_number[valences[1]]}\n"
        answer += f"{i}. " + "".join(elements) + get_name_compound(
            list(elements), list(elements2), base, valences[:-1], True) + "\n"
    return answer


def get_name_compound(elements, elements2: list, base: str, valences_elements: tuple, add_space: bool = False):
    ions = \
        {"H": "гидрид", "B": "борид", "O": "оксид", "At": "астатид",
         "Br": "бромид", "S": "сульфид", "Cl": "хлорид", "F": "фторид", "I": "иодид", "C": "карбид", "N": "нитрид",
         "Si": "силицид", "P": "фосфид", "As": "арсенид", "Se": "селенид", "Te": "теллурид", "N₃": "азид",
         "CO₃": "карбонат", "NO₃": "нитрат", "NO₂": "нитрит", "OH": "гидроксид",
         "PO₄": "фосфат (ортофосфат)", "PO₃": "метафосфат", "SiO₃": "силикат", "SO₃": "сульфит", "SO₄": "сульфат",
         "BrO₂": "бромит", "BrO₃": "бромат", "BrO": "гипобромит", "VO₃": "ванадат", "WO₄": "вольфрамат",
         "BeO₄": "бериллат", "S₂O₇": "дисульфат", "P₂O₇": "дифосфат (пирофосфат)",
         "Cr₂O₇": "дихромат", "IO₄": "периодат", "IO": "гипоиодит", "MnO₄": "перманганат",
         "BO₂": "метаборат", "BO₃": "борат", "CrO₄": "хромат", "CN": "цианид",
         "AsO₂": "метаарсенит", "AsO₃": "ортоарсенит", "AsO₄": "арсенат", "C₂O₄": "оксалат",
         "ClO₂": "хлорит", "ClO₃": "хлорат", "ClO₄": "перохлорат", "ClO": "гипохлорит",
         "HCO₃": "гидрокарбонат", "HSO₄": "гидросульфат", "HSO₃": "гидросульфит",
         "HPO₄": "гидрофосфат (гидроортофосфат)", "H₂PO₄": "дигидрофосфат (дигидроортофосфат)",
         "HPO₃": "фосфит", "H₂PO₂": "гипофосфит"}
    genitive_elements = \
        {"H": "водорода", "Li": "лития", "Be": "бериллия", "B": "бора", "C": "углерода", "N": "азота", "O": "кислорода",
         "F": "фтора", "Na": "натрия", "Mg": "магния", "Al": "алюминия", "Si": "кремния", "P": "фосфора", "S": "серы",
         "Cl": "хлора", "K": "калия", "Ca": "кальция", "Sc": "скандия", "Ti": "титана", "V": "вандия", "Cr": "хрома",
         "Mn": "марганца", "Fe": "железа", "Co": "кобальта", "Ni": "никеля", "Cu": "меди", "Zn": "цинка", "Ga": "галия",
         "Ge": "германия", "As": "мышьяка", "Se": "селена", "Br": "брома", "Rb": "рубидия", "Sr": "стронция",
         "Y": "иттрия", "Zr": "циркония", "Nb": "ниобия", "Mo": "молибдена", "Tc": "технеция", "Ru": "Рутения",
         "Rh": "родия", "Pd": "палладия", "Ag": "серебра", "Cd": "кадмия", "In": "индия", "Sn": "олова", "Sb": "сурьмы",
         "Te": "теллура", "I": "йода", "Cs": "цезия", "Ba": "бария", "Hf": "гафния", "Ta": "тантала", "W": "вольфрама",
         "Re": "рения", "Os": "осмия", "Ir": "иридия", "Pt": "платины", "Au": "золота", "Hg": "ртути", "Tl": "талия",
         "Pb": "свинца", "Bi": "висмута", "Po": "полония", "At": "астата", "Fr": "франция", "Ra": "радия",
         "Rf": "резерфордия", "Db": "дубния", "Sg": "сиборгия", "Bh": "бория", "Hs": "хассия", "Mt": "мейтнерия",
         "Ds": "дармштадтия", "Rg": "рентгения", "Cn": "коперниция", "Nh": "нихония", "Fl": "флеровия",
         "Mc": "московия", "Lv": "ливермория", "Ts": "теннессина", "Og": "оганесона",
         "La": "лантана", "Ce": "церия", "Pr": "празеодима", "Nd": "неодима", "Pm": "прометия", "Sm": "самария",
         "Eu": "европия", "Gd": "гадолиния", "Tb": "тербия", "Dy": "диспрозия", "Ho": "гольмия", "Er": "эрбия",
         "Tm": "тулия", "Yb": "иттербия", "Lu": "лютеция",
         "Ac": "актиния", "Th": "тория", "Pa": "протактиния", "U": "урана", "Np": "нептуния", "Pu": "плутония",
         "Am": "америция", "Cm": "кюрия", "Bk": "берклия", "Cf": "калифорния", "Es": "эйнштейния", "Fm": "фермия",
         "Md": "менделевия", "No": "нобелия", "Lr": "лоуренция"}
    names_acids = \
        {"HCl": "хлороводородная, или соляная,", "H₂S": "сероводородная", "H₂SO₃": "сернистая", "H₂SO₄": "серная",
         "HNO₂": "азотистая", "HNO₃": "азотная", "H₂CO₃": "угольная", "H₂SiO₃": "кремниевая",
         "HBr": "бромоводородная", "HF": "фтороводородная, или плавиковая,", "HI": "иодоводородная",
         "H₃PO₄": "ортофосфорная, или фосфорная,", "HPO₃": "метафосфорная",
         "H₂BrO₂": "бромистая", "HBrO₃": "бромноватая", "HBrO": "бромноватистая, или гипобромистая,",
         "HVO₃": "ванадиевая", "H₂WO₄": "вольфрамовая", "H₂S₂O₇": "дисерная", "H₂Cr₂O₇": "дихромовая",
         "H₄P₂O₇": "дифосфорная, или пирофосфорная", "HIO₄": "иодная", "HIO": "иодноватистая",
         "HMnO₄": "марганцовая", "HBO₂": "метаборная", "HAsO₂": "метамышьяковистая", "H₃BO₃": "ортоборная, или борная,",
         "H₃AsO₃": "ортомышьяковистая", "H₃AsO₄": "ортомышьяковая", "H₂CrO₄": "хромовая", "H₂ClO₂": "хлористая",
         "HClO₄": "хлорная", "HClO₃": "хлорноватая", "HClO": "хлорноватистая", "HCN": "циановодородная, или синильная,",
         "H₂C₂O₄": "этандиовая, или щавельная,", "HN₃": "азотистоводородная"}
    add = " - " if add_space else ""
    numbers = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
    name_compound = ions.get(base)
    _valence = f" ({numbers[valences_elements[0]]})" if len(valence(elements2[0])) != 1 else ""
    result = f"{add}{name_compound} {genitive_elements[elements2[0]]}{_valence}"

    if names_acids.get("".join(elements)):
        result += f" ({names_acids.get(''.join(elements))} кислота)"

    return result


def get_lcm(x: int, y: int, *args) -> int:
    if x > y:
        greater = x
    else:
        greater = y
    while True:
        if (greater % x == 0) and (greater % y == 0):
            lcm = greater
            break
        greater += 1
    return lcm if not args else get_lcm(lcm, args[0], *args[1:])


def valence(element: str) -> list[int]:
    valences = \
        {"H": [1], "He": 0, "Li": [1], "Be": [2], "B": [3], "C": [2, 4], "N": [1, 2, 3, 4, 5], "O": [2], "F": [1],
         "Ne": 0, "Na": [1], "Mg": [2], "Al": [3], "Si": [2, 4], "P": [3, 5], "S": [2, 4, 6], "Cl": [1, 3, 5, 7],
         "Ar": 0, "K": [1], "Ca": [2], "Sc": [3], "Ti": [2, 3, 4], "V": [2, 3, 4, 6], "Cr": [2, 3, 6],
         "Mn": [2, 3, 4, 6, 7], "Fe": [2, 3], "Co": [2, 3], "Ni": [2, 3, 4], "Cu": [1, 2], "Zn": [2], "Ga": [3],
         "Ge": [2, 4], "As": [3, 5], "Se": [2, 4, 6], "Br": [1, 3, 5, 7], "Kr": [2, 4, 6], "Rb": [1], "Sr": [2],
         "Y": [3], "Zr": [2, 3, 4], "Nb": [1, 2, 3, 4, 5], "Mo": [2, 3, 4, 5, 6], "Tc": [1, 2, 3, 4, 5, 6, 7],
         "Ru": [2, 3, 4, 5, 6, 7, 8], "Rh": [1, 2, 3, 4, 5], "Pd": [1, 2, 3, 4], "Ag": [1, 2, 3], "Cd": [2], "In": [3],
         "Sn": [2, 4], "Sb": [3, 5], "Te": [2, 4, 6], "I": [1, 3, 5, 7], "Xe": [2, 4, 6, 8], "Cs": [1], "Ba": [2],
         "Hf": [2, 3, 4], "Ta": [1, 2, 3, 4, 5], "W": [2, 3, 4, 5, 6], "Re": [1, 2, 3, 4, 5, 6, 7],
         "Os": [2, 3, 4, 5, 6, 8], "Ir": [1, 2, 3, 4, 5, 6], "Pt": [1, 2, 3, 4, 5], "Au": [1, 2, 3], "Hg": [2],
         "Tl": [1, 3], "Pb": [2, 4], "Bi": [3, 5], "Po": [2, 4, 6], "At": [1], "Rn": 0, "Fr": [1], "Ra": [2],

         # Лантаноиды
         "La": [3], "Ce": [3, 4], "Pr": [3, 4], "Nd": [3], "Pm": [3], "Sm": [2, 3], "Eu": [2, 3], "Gd": [3],
         "Tb": [3, 4], "Dy": [3], "Ho": [3], "Er": [3], "Tm": [2, 3], "Yb": [2, 3], "Lu": [3],

         # Актиноиды
         "Ac": [3], "Th": [2, 3, 4], "Pa": [4, 5], "U": [3, 4], "Np": [3, 4, 5, 6], "Pu": [2, 3, 4], "Am": [3, 4, 5, 6],
         "Cm": [3, 4], "Bk": [3, 4], "Cf": [2, 3, 4], "Es": [2, 3], "Fm": [2, 3], "Md": [2, 3], "No": [2, 3], "Lr": [3]}

    return list(valences[element])


def get_base_element(string: str):
    base_ions_keys = \
        ("HPO", "HSO", "HCO", "ClO", "AsO", "CN", "BO", "MnO", "IO", "CrO", "BeO", "WO", "VO", "BrO", "SO", "SiO", "PO",
         "OH", "NO", "CO", "F", "O", "Cl", "N", "Br", "I", "S", "Se", "C", "At", "H", "P", "As", "Te", "B", "Si")
    electronegativity = \
        ("Fr", "Cs", "K", "Rb", "Ba", "Ra", "Na", "Sr", "Li", "Ca", "La", "Ac", "Yb", "Ce", "Pr", "Pm", "Am", "Nd",
         "Sm", "Gd", "Dy", "Y", "Er", "Tm", "Lu", "Cm", "Pu", "Th", "Bk", "Cf", "Es", "Fm", "Md", "No", "Hf", "Mg",
         "Zr", "Np", "Sc", "U", "Ta", "Pa", "Ti", "Mn", "Be", "Nb", "Al", "Tl", "Zn", "V", "Cr", "Cd", "In", "Ga", "Fe",
         "Pb", "Co", "Cu", "Re", "Si", "Tc", "Ni", "Ag", "Sn", "Hg", "Po", "Bi", "B", "Sb", "Te", "Mo", "As", "P", "H",
         "Ir", "Rn", "At", "Ru", "Pd", "Os", "Pt", "Rh", "W", "Au", "C", "Se", "S", "Xe", "I", "Kr", "Br", "N", "Cl",
         "O", "F")
    base_ions = \
        {"H": "H", "B": "B", "O": "O", "At": "At", "Br": "Br", "S": "S", "Cl": "Cl", "F": "F", "I": "I", "C": "C",
         "N": ["N", "N₃"], "Si": "Si", "P": "P", "As": "As", "Se": "Se", "Te": "Te",
         "CO": ["CO₃", "C₂O₄"], "NO": ["NO₂", "NO₃"], "OH": ["OH"], "PO": ["PO₃", "PO₄", "P₂O₇"], "SiO": ["SiO₃"],
         "SO": ["SO₃", "SO₄", "S₂O₇"], "BrO": ["BrO", "BrO₂", "BrO₃"], "VO": ["VO₃"], "WO": ["WO₄"],
         "BeO": ["BeO₄"], "CrO": ["CrO₄", "Cr₂O₇"], "IO": ["IO", "IO₄"], "MnO": ["MnO₄"], "BO": ["BO₂", "BO₃"],
         "CN": ["CN"], "AsO": ["AsO₂", "AsO₃", "AsO₄"], "ClO": ["ClO", "ClO₂", "ClO₃", "ClO₄"],
         "HCO": ["HCO₃"], "HSO": ["HSO₃", "HSO₄"], "HPO": ["HPO₃", "HPO₄", "H₂PO₄", "H₂PO₂"]}
    variants_base_element = []
    base_ion = ""
    for ion in base_ions_keys:
        bool_ion = True
        for i in get_elements(ion, True):
            if i not in get_elements(string, True):
                bool_ion = False
        if bool_ion and sorted(get_elements(ion, True)) != \
                sorted(get_elements(string, True)):
            base_ion = ion
            variants_base_element.append(base_ions[ion])
            break
    for element in variants_base_element:
        if type(element) == list:
            return element, base_ion
    variants_base_element = get_elements(string, True)
    base_element = electronegativity[max(*[electronegativity.index(element) for element in variants_base_element])]
    if base_element not in base_ions_keys:
        raise ValueError
    return [base_element], base_element


def gas_density(string: str) -> ResultCalculate:
    number_to_index = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈",
                       "9": "₉"}
    nti = lambda i: "".join([number_to_index.get(j, j) for j in i])
    answer, mass = molecular_weight(string, get_elements(string))
    answer += f"\nρ({nti(string)}) = M({nti(string)}) / Vm = {mass} г/моль / 22.4 л/моль = " \
              f"<b>{round(mass / 22.4)} г/л</b>"
    result = round(mass / 22.4)
    return ResultCalculate(answer, result)


def amount_of_substance_from_volume_of_gas(volume: str) -> ResultCalculate:
    answer = f"n = V / Vm\nn = {volume} / 22.4 л/моль = <b>{round(Volume(volume).get_volume('л') / 22.4)} моль</b>"
    result = round(Volume(volume).get_volume('л') / 22.4)
    return ResultCalculate(answer, result)


def amount_of_substance_from_number_of_particles(string: str) -> ResultCalculate:
    number: int = eval(string, {"__builtins__": {}}, {})
    number = int(number) if int(number) == number else number
    answer = f"n = N / Nₐ = {string} / 6.02 * 10²³ моль⁻¹ = " \
             f"<b>{round(number / (6.02 * 10 ** 23))}моль</b>"

    return ResultCalculate(answer, round(number / (6.02 * 10 ** 23)))


def amount_of_substance_from_mass(weight: str, string: str) -> ResultCalculate:
    number_to_index = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈",
                       "9": "₉"}
    nti = lambda i: "".join([number_to_index.get(j, j) for j in i])
    weight = Weight(weight)
    Mr = molecular_weight(string, get_elements(string)).result
    answer = f"1. M({nti(string)}) = Mr({nti(string)}) г/моль = {Mr} г/моль\n" \
             f"2. n({nti(string)}) = m / M = {weight} / {Mr}г/моль = " \
             f"<b>{round(weight.get_mass('г') / Mr)}моль</b>"

    return ResultCalculate(answer, round(weight.get_mass('г') / Mr))


def volume_fraction(volume_part: str, volume_mixture: str) -> ResultCalculate:
    result = round(Volume(volume_part).get_volume('м³') /
                   Volume(volume_mixture).get_volume('м³'))
    answer = f"φ = {volume_part} / {volume_mixture} " \
             f"= {result} = <b>{result * 100}%</b>"
    return ResultCalculate(answer, result)


def mass_fraction(string: str, element: str, elements: list[str]) -> ResultCalculate:
    number_to_index = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈",
                       "9": "₉"}
    nti = lambda i: "".join([number_to_index.get(j, j) for j in i])
    Mr = molecular_weight(string, elements)
    n = elements.count(element)
    result = f"1. {Mr.answer}\n2. ω({element}) = Aᵣ({element}) * n({element}) / Mᵣ({nti(string)}) * 100% = " \
             f"{Ar(element)} * {n} / {Mr.result} * 100% = <b>{round(Ar(element) * n / Mr.result * 100)}%</b>"

    return ResultCalculate(result, round(Ar(element) * n / Mr.result))


def molecular_weight(string: str, elements: list[str]) -> ResultCalculate:
    number_to_index = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈",
                       "9": "₉"}
    nti = lambda i: "".join([number_to_index.get(j, j) for j in i])
    answer = f"Mᵣ({nti(string)}) = "
    set_elements = []
    for element in elements:
        if element not in set_elements:
            set_elements.append(element)
    for element in set_elements:
        if elements.count(element) == 1:
            answer += f"Aᵣ({element}) + "
        else:
            answer += f"{elements.count(element)}Aᵣ({element}) + "
    answer = list(answer)
    answer[-2] = "="
    answer = "".join(answer)
    weights = []
    for element in set_elements:
        weights.append(Ar(element))
    string = answer.split("= ")[1][:-1]
    string = re.sub(r'(\d+)A', r'\1 * A', string)
    Ars = re.findall(r'Aᵣ\(\w+\)', string)
    for ar in Ars:
        string = string.replace(ar, str(Ar(ar[3:-1])))
    answer += string + " = " + f"<b>{eval(string)}</b>"
    result = eval(string)
    return ResultCalculate(answer, result)


def Ar(element: str) -> int:
    relative_molecular_weights = \
        {"H": 1, "He": 4, "Li": 7, "Be": 9, "B": 11, "C": 12, "N": 14, "O": 16, "F": 19, "Ne": 20,
         "Na": 23, "Mg": 24, "Al": 27, "Si": 28, "P": 31, "S": 32, "Cl": 35.5, "Ar": 40,
         "K": 39, "Ca": 40, "Sc": 45, "Ti": 48, "V": 51, "Cr": 52, "Mn": 55, "Fe": 56, "Co": 59, "Ni": 59,
         "Cu": 64, "Zn": 65, "Ga": 70, "Ge": 73, "As": 75, "Se": 79, "Br": 80, "Kr": 84,
         "Rb": 85, "Sr": 88, "Y": 89, "Zr": 91, "Nb": 93, "Mo": 96, "Tc": 98, "Ru": 101, "Rh": 103, "Pd": 106,
         "Ag": 108, "Cd": 112, "In": 115, "Sn": 119, "Sb": 122, "Te": 128, "I": 127, "Xe": 131,
         "Cs": 133, "Ba": 137, "Hf": 178, "Ta": 181, "W": 184, "Re": 186, "Os": 190, "Ir": 192, "Pt": 195,
         "Au": 197, "Hg": 201, "Tl": 204, "Pb": 207, "Bi": 209, "Po": 209, "At": 210, "Rn": 222,
         "Fr": 223, "Ra": 226, "Rf": 261, "Db": 262, "Sg": 266, "Bh": 267, "Hs": 269, "Mt": 268, "Ds": 271,
         "Rg": 282, "Cn": 285, "Nh": 286, "Fl": 289, "Mc": 288, "Lv": 293, "Ts": 294, "Og": 294,

         # Лантаноиды
         "La": 139, "Ce": 141, "Pr": 141, "Nd": 144, "Pm": 145, "Sm": 150, "Eu": 152, "Gd": 157, "Tb": 159, "Dy": 163,
         "Ho": 165, "Er": 167, "Tm": 169, "Yb": 173, "Lu": 175,

         # Актиноиды
         "Ac": 227, "Th": 232, "Pa": 231, "U": 238, "Np": 237, "Pu": 244, "Am": 243, "Cm": 247, "Bk": 247, "Cf": 251,
         "Es": 252, "Fm": 257, "Md": 258, "No": 259, "Lr": 260}
    return relative_molecular_weights[element]


def get_elements(string: str, _set: bool = False) -> list[str]:
    numbers = {"₂": "2", "₃": "3", "₄": "4", "₇": "7"}
    elements = []
    i = 0
    if string.count("(") or string.count(")"):
        if string.count("(") - 1 or string.count(")") - 1:
            raise ValueError()
        inside_string = string[string.index("(") + 1:string.index(")")]
        coefficient = int(string[string.index(")") + 1])
        inside_elements = get_elements(inside_string) * coefficient
        string = string.replace(f"({inside_string}){coefficient}", "")
        elements = get_elements(string) + inside_elements

        if not _set:
            return elements
        set_elements = []
        for element in elements:
            if element not in set_elements:
                set_elements.append(element)
        return set_elements

    while i < len(string):
        element = ""
        change_i = False
        for n in range(i + 1, len(string)):
            if string[n].isupper():
                element = string[i:n]
                i = n
                change_i = True
                break
        if not change_i:
            element = string[i:len(string)]
            i = len(string)

        coefficient = 1
        for n in str(element):
            if n.isnumeric():
                element, coefficient = element[0:element.index(n)], int(numbers.get(element[element.index(n):],
                                                                                    element[element.index(n):]))
                break
        elements += [element] * coefficient

    for element in elements:
        Ar(element)

    if not _set:
        return elements
    set_elements = []
    for element in elements:
        if element not in set_elements:
            set_elements.append(element)
    return set_elements


Inf = EducationalInformation
Text = TextEducationalInformation
Photo = PhotoEducationalInformation


def answer_text(text: str):
    async def fun(message: Message):
        await message.answer(text, parse_mode=markdown)

    return fun


functions = {
    'physics7': EducationalData(
        text=None,
        data_path=DataPath('physics7'),
        concepts_physics=EducationalData(
            text="Базовые понятия",
            data_path=DataPath('physics7', 'concepts_physics'),
            physical_body=Inf("Физ. тело", "*Физическое тело* - каждое из окружающих нас предметов"),
            substance=Inf("Вещество", "*Вещество* - то, из чего состоит физическое тело"),
            physical_phenomenon=Inf(
                "Физ. явление",
                "*Физическое явление* - любое изменение, происходящее с телом. Физические явления делятся на "
                "механические, звуковые, тепловые, электрические, магнитные, световые, атомные"),
            physical_quantity=Inf(
                "Физ. величина",
                "*Физическая величина* - количественная характеристика физического тела или явления"),
            price_of_division=Inf(
                "Цена деления",
                "Чтобы определить цену деления прибора (c) нужно\n"
                "1) найти 2 ближайших штриха шкалы, у которых определены значения величины\n"
                "2)вычесть из большего меньшее и полученное значение разделить на число делений между ними"),
            meaning_of_prefixes=Inf("Приставки", Photo("Prefixes/prefixes.png")),
            measurement_error=Inf("Погрешность", Text(
                "<b>Погрешность измерения</b> - допускаемая неточность при проведении измерения\n"
                "A = a&#177&#916a\n"
                "A - измеряемая величина\n"
                "a - результат измерений\n"
                "&#916a - погрешность измерения\n"
                "&#916a = 0.5с (цена деления прибора)", parse_mode=html)),
            structure_of_matter=EducationalData(
                text="Строение вещества",
                data_path=DataPath('physics7', 'concepts_physics', 'structure_of_matter'),
                molecule=Inf("Молекула", "*Молекула* - мельчайшая частица определенного вещества"),
                atom=Inf("Атом", "*Атом* - мельчайшая неделимая частица, состоящая из элементарных частиц"),
                diffusion=Inf(
                    "Диффузия",
                    "*Диффузия* - явление, при котором происходит взаимное проникновение молекул одного вещества между "
                    "молекулами другого вещества\n"
                    "Скорость диффузии прямо пропорционально температуре"),
                brownian_motion=Inf(
                    "Броуновское движение",
                    "*Броуновское движение* - беспорядочное движение молекул в веществе. "
                    "*Броуновское движение никогда не заканчивается!*"),
                wetting=Inf(
                    "Смачивание",
                    "*Смачивание* - явление, при котором молекулы жидкости притягиваются друг к "
                    "другу слабее, чем к молекулам твердого тела"),
                non_wetting=Inf(
                    "Несмачивание",
                    "*Несмачивание* - явление, при котором молекулы жидкости притягиваются друг к "
                    "другу сильнее, чем к молекулам твердого тела")
            )
        ),
        mechanic=EducationalData(
            text="Механика",
            data_path=DataPath('physics7', 'mechanic'),
            movement=Inf("Механ. движение",
                         "*Механическое движение* - изменение со временем положения тела относительно других тел"),
            trajectory=Inf("Траектория",
                           "*Траектория* - линия, по которой движется тело. Траектории делятся на прямолинейные и "
                           "криволинейный и на видимые и невидимые"),
            path_traveled=Inf("Путь",
                              "*Пройденный путь* (S) - длина траектории, по которой двигалось тело в "
                              "течении промежутка времени"),
            uniform_movement=Inf("Равном. движение",
                                 "*Равномерное движение* - движение тела, которое проходит за любые равные "
                                 "промежутки времени равные пути"),
            uneven_movement=Inf("Неравном. движение",
                                "*Неравномерное движение* - движение тела, которое проходит за какие-нибудь "
                                "равные промежутки времени разные пути"),
            speed=Inf("Скорость",
                      "*Скорость* - физическая величина, характеризующая быстроту движения тела"),
            formulas=Inf("Формулы",
                         Text("Скорость: U = S / t\nРасстояние: S = U * t\nВремя: t = S / U\nU - скорость\n"
                              "S - расстояние\nt - скорость", parse_mode=html)),
            inertia=Inf("Инерция",
                        "*Инерция* - явление сохранения скорости тела при отсутствии действия на него других тел\n"
                        "*Инертность* - свойство тел сохранять свою скорость\n*Масса* (m) - физическая величина, "
                        "характеризующая инертность тела")
        ),
        density=Inf("Плотность",
                    Text("<b>Плотность</b> - физическая величина, которая равна отношению массы тела к его объему\n"
                         "Плотность: &#961 = m / V\nМасса: m = &#961 * V\nОбъем: V = m / &#961", parse_mode=html)),
        force=EducationalData(
            text="Сила",
            data_path=DataPath('physics7', 'force'),
            force=Inf("Сила",
                      "*Сила* (F) - мера взаимодействия тел. Результат действия силы на тело "
                      "зависит от ее модуля, направления и точки приложения\n[F] = H (Ньютон)"),
            deformation=Inf("Деформация",
                            "*Деформация* - изменение формы и (или) размеров тела. Деформация делится на "
                            "*Пластическую* и *Упругую*\n*Пластическая деформация* - деформация без "
                            "возвращения в первоначальное состояние\n*Упругая деформация* - деформация с "
                            "возвращение в первоначальное состояние"),
            strength_of_elasticity=Inf("Сила упругости",
                                       Text("<b>Сила упругости</b> - сила, возникающая в результате его упругой "
                                            "деформации и стремящаяся вернуть тело в первоначальное состояние\n"
                                            "Сила упругости: F = k * &#916l\nk - жесткость тела\n&#916l - "
                                            "изменение в длине тела", parse_mode=html)),
            law_of_hook=Inf("Закон Гука",
                            "Модуль силы упругости при растяжении или сжатии тела прямо "
                            "пропорционален изменению длины тела"),
            gravity=Inf("Сила тяжести",
                        Text("<b>Сила тяжести</b> - сила, с которой космический объект в близи своей "
                             "поверхности притягивает к себе тело\nСила тяжести: F = g * m\ng - "
                             "ускорение свободного падения в близи поверхности данного космического "
                             "тело (~9.8 на Земле)\nm - масса тела", parse_mode=html)),
            body_weight=Inf("Вес тела",
                            Text("<b>Вес тела</b> - сила, с которой тело вследствие притяжении к космическому телу "
                                 "действует на опору или подвес\nВес тела: P = g * m (без учета силы Архимеда)\n"
                                 "Вес тела: P = g * (m - &#961 * V)\ng - ускорение свободного падения в близи "
                                 "поверхности данного космического тело (~9.8 на Земле)\nm - масса тела\n"
                                 "&#961 - плотность жидкости или газа\nV - объем тела", parse_mode=html)),
            friction_force=Inf("Сила трения",
                               "*Трение* - взаимодействие тел, препятствующее их относительному движению\n"
                               "Трения делятся на *трение покоя*, *трение скольжения* и *трение качения*\n"
                               "*Трение покоя* - трение возникающее между покоящимися относительно друг "
                               "друга телами\n*Трение скольжения* - трение, возникающее при скольжении\n"
                               "*Трение качения* - трение, возникающее, когда тело катится"),
            resultant_of_forces=Inf("Равнодействующая",
                                    "*Равнодействующая сил* - сила, которая производит на тело такое же действие,"
                                    " как несколько одновременно действующих сил\nРавнодействующая сил: "
                                    "R = F1 + F2 + ... Fn"),
            power_of_Archimedes=Inf("Сила Архимеда",
                                    Text("<b>Сила Архимеда</b> - выталкивающая сила действующая на тело, погруженное "
                                         "в жидкость или газ\nСила Архимеда: F = g * &#961 * V\ng - ускорение "
                                         "свободного падения в близи поверхности данного космического тело (~9.8 на "
                                         "Земле)\n&#961 - плотность жидкости или газа\nV - объем тела", html)),
        ),
        pressure=EducationalData(
            text="Давление",
            data_path=DataPath('physics7', 'pressure'),
            pressure=Inf("Давление",
                         "*Давление* (p) - физическая величина, которая равна отношению силы, "
                         "действующей перпендикулярно поверхности, к площади поверхности\nДавление"
                         ": p = F / S\nF - сила действующая перпендикулярно поверхности\nS - "
                         "площадь поверхности\n[p] = Па (Паскаль)"),
            gas_pressure=Inf("Давление газа",
                             "Давление газа на стенки сосуда и помещенное в газ тело вызывается ударами "
                             "молекул газа. Газ давит на стенки сосуда по всем направлениям одинаково. "
                             "Давление газа прямо пропорционально температуре"),
            liquid_pressure=Inf("Давление жидкости",
                                Text("Внутри жидкости существует давление на стенки сосуда и на помещенное в "
                                     "жидкость тело. На одном и том же уровне давление жидкости одинаково. С "
                                     "глубиной давление увеличивается\nДавление жидкости: p = g * &#961 * h\n"
                                     "космического тело (~9.8 на Земле)\n&#961 - плотность жидкости\nh - "
                                     "высота, на которую погружено тело", parse_mode=html)),
            law_of_pascal=Inf("Закон Паскаля",
                              "Давление, производимое на жидкость или газ, передается в любую точку без "
                              "изменений во всех направлениях"),
            atmospheric_pressure=Inf("Атмосф. давление",
                                     Text("<b>Атмосферное давление</b> - давление газов в атмосфере космического "
                                          "тела\n1 мм ртутного столба = 133.3 Па\nБарометр - прибор для измерения "
                                          "атмосферного давления\nНормальное атмосферное давление на Земле при "
                                          "температуре 0&#176C и на уровне море. Атмосферное давление обратно "
                                          "пропорционально высоте над уровнем моря", parse_mode=html)),
            swimming_bodies=Inf("Плавание тел",
                                Photo('Floating Bodies/body_swimming.png')),
            communicating_vessels=Inf("Сообщающиеся сосуды",
                                      Photo('Floating Bodies/communicating vessels.png'))
        ),
        job=EducationalData(
            text="Механическая работа",
            data_path=DataPath('physics7', 'job'),
            job=Inf("Механическая работа",
                    "*Механическая работа* (A) – это физическая величина, описывающая действие "
                    "одного тела на другое на некотором участке траектории\nМеханическая работа: "
                    "A = cos a * F * S\ncos a - косинус угла между между направлением силы и "
                    "траекторией движения тела\nF - сила действующая на тело\nS - пройденный "
                    "телом путь\n[A] = Дж (Джоуль)"),
            power=Inf("Мощность",
                      "*Мощность* (N) - физическая величина, характеризующая быстроту выполнения "
                      "работы\nМощность: N = A / t\nA - работа, совершенная за промежуток времени\n"
                      "t - промежуток времени\n[N] = Вт (Ватт)"),
            simple_mechanisms=Inf("Простые механизмы",
                                  "*Простые механизмы* - механизмы, служащие для преобразовании силы. "
                                  "Примеры: рычаг, блок, наклонная плоскость\n*Простые механизмы не "
                                  "выигрывают в работе!*"),
            lever=Inf("Рычаг",
                      Photo('Mechanical Work/lever arm.png',
                            Text("*Рычаг* - твердое тело, которое может вращаться вокруг неподвижной опоры\n"
                                 "*Плечо силы* - кратчайшее расстояние между точкой опоры и прямой, вдоль "
                                 "которой действует сила"))),
            lever_balance=Inf("Равновесие рычага",
                              Text("Момент силы: M  = F * l\nF - сила действующая на плечо рычага\nl - плечо "
                                   "силы. Равновесие рычага происходит, когда моменты сил равны", parse_mode=html)),
            energy=Inf("Энергия",
                       "*Механическая энергия* (E) делится на *Потенциальную* и *Кинетическую*\n"
                       "*Потенциальная энергия* - энергия взаимодействия\n*Кинетическая энергия*"
                       " - энергия движения\nПотенциальная энергия: E = g * m * h\ng - ускорение"
                       " свободного падения в близи поверхности данного космического тело "
                       "(~9.8 на Земле)\nm - масса тела\nh - высота\nКинетическая энергия: E = "
                       "m * U * U / 2\nm - масса тела\nU - скорость движения тела"),
            law_of_conservation_of_energy=Inf("Закон сохранения энергии",
                                              "При отсутствии сил сопротивления полная механическая энергия становится "
                                              "величиной постоянной")
        )
    ),
    'physics8': EducationalData(
        text=None,
        data_path=DataPath('physics8'),
        mkt=EducationalData(
            text="МКТ",
            data_path=DataPath('physics8', 'mkt'),
            mkt=Inf("МКТ",
                    "*МКТ* - молекулярно-кинетическая теория\nМКТ изучает тепловые явления\n"
                    "Основоположник МКТ - Демокрит\n*Молекула* - мельчайшая частица данного "
                    "вещества, обладающая всеми его свойствами. Молекулы бывают простыми и "
                    "сложными"),
            main_provisions_of_mkt=Inf("Основные положения",
                                       "*Основные положения МКТ*\n"
                                       "*1.* Все тела состоят из молекул, между которыми имеются промежутки. "
                                       "Доказательства: _сжимаемость газа, тепловое расширение тел_\n"
                                       "*2.* Молекулы находятся в непрерывном движении. Доказательства: "
                                       "_диффузия, Броуновское движение_\n"
                                       "*3.* Молекулы взаимодействуют между собой. Доказательства: _агрегатные "
                                       "состояния вещества_"),
            aggregate_states_of_matter=Inf("Агрегатные состояния вещества",
                                           Photo('MKT/states_of_matter.png',
                                                 Text("*Агрегатные состояния вещества:*\n"
                                                      "1. Твердое\n"
                                                      "2. Жидкое\n"
                                                      "3. Газообразное"))),
            crystalline_and_amorphous_bodies=Inf("Кристаллические и аморфные тела",
                                                 Photo('MKT/solids.png',
                                                       Text("Твердые тела делятся на *кристаллические* и *аморфные*")))
        ),
        thermal_phenomena=EducationalData(
            text="Тепловые явления",
            data_path=DataPath('physics8', 'thermal_phenomena'),
            internal_energy=Inf("Внутрення энергия",
                                "*Внутренняя энергия тела* (U) - кинетическая энергия всех молекул, из которых состоит "
                                "тело, и потенциальная энергия их взаимодействия\nВнутренняя энергия зависит от от "
                                "температуры, агрегатного состояния и других факторов. Внутренняя энергия тела не "
                                "зависит от механического движения тела и от положения данного тела относительно "
                                "других тел"),
            change_in_internal_energy=Inf("Изменение U",
                                          "*Внутренняя энергия тела прямо пропорциональна температуре тела*. Внутреннюю"
                                          " энергию можно изменить путем совершения работы или теплопередачей\nЕсли "
                                          "работу совершает само тело, то внутренняя энергия тела уменьшается. Если над"
                                          " телом совершают работу, то внутренняя энергия тела увеличивается. *Если "
                                          "между телами происходит теплообмен, то сумма внутренней энергии всех тел, "
                                          "участвующих в теплообмене, не изменяется*\nТеплопередача всегда происходит "
                                          "от тел с более высокой температурой к телам с более низкой!"),
            heat_transfer=Inf("Теплопередача",
                              "*Теплопередача* - процесс изменения внутренней энергии без совершения работы над телом "
                              "или самим телом\nТеплопередача делится на *теплопроводность*, *конвекцию* и *излучение*"),
            thermal_conductivity=Inf("Теплопроводность",
                                     "*Теплопроводность* - явление передачи внутренней энергии от одной части "
                                     "тела к другой или от одного тела к другому при их непосредственном контакте"),
            convection=Inf("Конвекция",
                           Photo('Thermal Phenomena/convection.png',
                                 Text("*Конвекция* - явление передачи внутренней энергии переносом струй газа "
                                      "или жидкости\nГорячие струи внизу начинают подниматься вверх, а холодные"
                                      " струи - вниз. Таким образом струи с разной температурой перемешиваются"
                                      "\n*Конвекция невозможна при нагревании сверху*"))),
            radiation=Inf("Излучение",
                          "*Излучение* — передача энергии электромагнитными волнами, испускаемыми "
                          "телами за счёт их внутренней энергии. Конвекция происходит даже при "
                          "отсутствии контакта например, в вакууме\nТела с темной поверхностью "
                          "быстрее меняют свою температуру путем излучения, а тела со светлой "
                          "поверхностью - медленнее"),
            evaporation=Inf("Испарение",
                            "*Парообразование* - явление превращения жидкости в пар\n"
                            "*Испарение* - парообразование, происходящее с поверхности жидкости. "
                            "Испарение понижает температуру жидкости\n"
                            "*Насыщенный пар* - пар, находящийся в динамическом равновесии со своей "
                            "жидкостью\n"
                            "*Ненасыщенный пар* - пар, не находящийся в динамическом равновесии со "
                            "своей жидкостью\n"
                            "*Конденсация* - явление превращения пара в жидкость\n"
                            "*Кипение* - интенсивный переход жидкости в пар, происходящий с "
                            "образованием пузырьков пара по всему объему жидкости при определенной "
                            "температуре. Во время кипения температура не меняется! "
                            "Атмосферное давление прямо пропорционально температуре кипения\n"
                            "*Точка росы* - температура, при которой пар, находящийся в воздухе, "
                            "становится насыщенным"),
            quantities=EducationalData(
                text="Физические величины",
                data_path=DataPath('physics8', 'thermal_phenomena', 'quantities'),
                amount_of_heat=Inf("Количество теплоты",
                                   "*Количество теплоты* (Q) - энергия, которую получает или теряет тело при"
                                   " теплопередаче\nКоличество теплоты, которое нужно затратить, чтобы "
                                   "изменить температуру, прямо пропорционально массе тела\nQ = [ Дж ]"),
                calories=Inf("Калория",
                             Text("<b>Калория</b> - количество теплоты, которое необходимо для нагревания "
                                  "1г воды на 1&#176C\n1 кал = 4.19 Дж", parse_mode=html)),
                heat_capacity=Inf("Удельная теплоемкость",
                                  Text("<b>Удельная теплоемкость вещества</b> (c) - физическая величина, "
                                       "равная количеству теплоты, которое необходимо передать телу массой "
                                       "1кг для того, чтобы его температура изменилась на 1&#176C\n"
                                       "c = [Дж / (кг * &#176C]\n"
                                       "Удельная теплоемкость: c = Q / (m * t)\nQ - количество теплоты\nm - "
                                       "масса\nt - изменение температуры тела\nКоличество теплоты: "
                                       "Q = c * m * t\nc - удельная теплоемкость тела\nm - масса тела\nt - "
                                       "изменение температуры\n/heat_capacity - таблица", parse_mode=html)),
                heat_of_combustion=Inf(
                    "Удельная теплота сгорания топлива",
                    "*Удельная теплота сгорания топлива* (q) - физическая величина, "
                    "показывающая, какое количество теплоты выделяется при полном сгорании "
                    "топлива массой 1кг\nq = [Дж / кг]\nУдельная теплота сгорания топлива: "
                    "q = Q / m\nQ - количество теплоты\nm - масса тела\n/fuel - таблица"),
                heat_of_melting=Inf(
                    "Удельная теплота плавления",
                    Text("<b>Удельная теплота плавления</b> (&#955) - физическая величина, показывающая, какое "
                         "количество теплоты необходимо сообщить кристаллическому телу массой 1кг, чтобы при "
                         "температуре плавления полностью перевести его в жидкое состояние\n&#955 = [Дж / кг]\n"
                         "Удельная теплота плавления&#955 = Q / m\nQ - количество теплоты\nm - масса тела\n"
                         "/melting - таблица", parse_mode=html)),
                heat_of_vaporization=Inf("Удельная теплота парообразования",
                                         "*Удельная теплота парообразования* (L) - физическая величина, "
                                         "показывающая, какое количество теплоты необходимо сообщить жидкость "
                                         "массой 1 кг, чтобы пр  температуре кипения полностью перевести его в"
                                         " газообразное состояние\nL = [Дж / кг]\nУдельная теплота "
                                         "парообразования:L = Q / m\nQ - количество теплоты\nm - масса тела\n"
                                         "/vaporization - таблица")
            )
        ),
        electrical_phenomena=EducationalData(
            text="Электрические явления",
            data_path=DataPath('physics8', 'electrical_phenomena'),
            main_provisions=Inf("Основные положения",
                                Photo('Electrical Phenomena/atomic_structure.png',
                                      Text("*Электризация* - сообщение телу электрического заряда. Электризация "
                                           "происходит при их соприкосновении - электроны переходят с одного тела на "
                                           "другое из-за того, что у одного вещества притяжение электронов к ядру "
                                           "сильнее, а у другого - слабее"))),
            electric_charge=Inf("Электрический заряд",
                                "*Электрический заряд* бывает положительным или отрицательным. Тела, имеющие одинаковые"
                                " электрические заряды одинакового знака, взаимно отталкиваются, а разного - взаимно "
                                "притягиваются. Любое заряженное тело окружено электрическим полем\n*Электрическое поле"
                                "* - особый вид материи. Сила, с которой действует электрическое поле на внесенный в "
                                "него электрический заряд\n*Электрон* - частица, имеющая самый маленький заряд\nЗаряд "
                                "атомов равен нулю, т. к. абсолютное значение протонов равно значению электронов. При "
                                "изменений количества электронов атом получает заряд и становится положительным или "
                                "отрицательным ионом"),
            electric_current=Inf("Электрический ток",
                                 Photo('Electrical Phenomena/electricity.png',
                                       Text("*Электрический ток* - направленное движение заряженных частиц\nВ металле "
                                            "расположены положительные ионы и отрицательные электроны, поэтому металл в"
                                            " состоянии покоя электрически нейтрален"))),
            electrical_circuit=Inf("Электрическая цепь",
                                   Photo('Electrical Phenomena/electrical_circuit.png',
                                         Text("*Электрическая цепь* состоит из\n1) источник тока (батарейка)\n"
                                              "2) приемник тока (лампа)\n"
                                              "3) замкнутая цепь проводника (провода)\n"
                                              "4) замыкающие / размыкающие устройства "
                                              "(рубильник)\n5) другие элементы"))),
            current_actions=Inf("Действия тока",
                                "*Действия тока* - явления, вызываемые электрическим током\n*Тепловые действия тока* - "
                                "в некоторых проводниках под действием тока происходит нагрев\n*Химические действия "
                                "тока* - в некоторых проводниках под действие электрического тока происходят химические"
                                " реакции\n*Магнитное действие тока* - во всех проводниках под действием электрического"
                                " тока образуется магнитное поле. Подробнее в разделе электромагнитные явления"),
            guides=Inf("Проводники",
                       "*Свободные электроны* - электроны, которые покинули свое место в атоме из-за слабого "
                       "притяжения и удаленного расположения\n*Проводники* - тела, через которые электрические "
                       "заряды могут переходить от заряженного тела к незаряженному (вещества со свободными "
                       "электронами)\n*Полупроводники* - тела, которые по способности передавать электрические "
                       "заряды занимают промежуточное положение между проводниками и непроводниками\n"
                       "*Непроводники (диэлектрики)* - тела, через которые электрические заряды не могут "
                       "переходить от заряженного тела к незаряженному (вещества без свободных электронов)"),
            charge=Inf("Заряд",
                       Text("<b>Заряд, или количество электричества, (q)</b> - физическая величина, "
                            "определяющая силу электромагнитного взаимодействия. q = [Кл] (кулон). "
                            "Электрический заряд электрона (е) = 1.6*10⁻¹⁹ Кл", parse_mode=html)),
            current_strength=Inf("Сила тока",
                                 "*Сила тока (I)* - физическая величина, характеризующая скорость "
                                 "прохождения электрического заряда через поперечное сечение проводника "
                                 "за 1с. I = q/t. I = [A] (ампер)"),
            forward=EducationalData(
                text="Дальше",
                data_path=DataPath('physics8', 'electrical_phenomena', 'forward'),
                voltage=Inf("Напряжение",
                            "*Работа тока (A)* - работа сил электрического поля, создающего "
                            "электрический ток. A = [Дж]\n"
                            "*Электрическое напряжение (U)* - физическая величина, характеризующая "
                            "электрическое поле. U = A/q. U = [Дж/Кл] = [В] (вольт)\n"
                            "Напряжение показывает, какую работу совершает электрическое поле при "
                            "перемещении единичного положительного электрического заряда из одной "
                            "точки в другую\nСила тока в проводнике прямо пропорциональна напряжению "
                            "на концах проводника. Сила тока также зависит от сопротивления в проводнике"),
                resistance=Inf("Сопротивление",
                               Text("<b>Электрическое сопротивление (R)</b> - физическая величина, "
                                    "показывающая, какое напряжение на концах проводника при силе тока в 1А. "
                                    "R = U/I. R = [В/А] = [Ом] (Ом). Сила тока в проводнике обратно "
                                    "пропорциональна электрическому сопротивлению\n"
                                    "R=pl/S, где p - удельное сопротивление проводника, l - длина проводника,"
                                    " S - площадь поперечного сечения проводника\n<b>Удельное сопротивление "
                                    "проводника (p)</b> - физическая величина, характеризующая сопротивление "
                                    "проводника длиной 1м и площадью поперечного сечения 1м². p = [Ом*м] или "
                                    "Ом*мм²/м (чаще всего)", parse_mode=html)),
                law_of_om=Inf("Закон Ома",
                              "Электрическое сопротивление прямо пропорционально длине проводника и "
                              "обратно пропорционально площади поперечного сечения проводника "
                              "(а также завит от вещества проводника)"),
                rheostat=Inf("Реостат",
                             Photo('Electrical Phenomena/rheostat.png',
                                   Text("*Реостат* - специальный прибор, служащий для регулирования силы тока в "
                                        "цепи путем изменения сопротивления"))),
                current_operation=Inf("Работа тока",
                                      Text("Работа тока (A) = U*q = U*I*t (напряжение * сила тока * время)", html)),
                units_of_work=Inf("Единицы работы",
                                  Text("<b>Единицы работы, применяемые на практике</b>\n1 Вт = 1 Дж/с => 1 Дж = "
                                       "1 Вт * с. На практике чаще всего используется единица измерения Вт*ч и "
                                       "КВт*ч. Вт*ч = 3600 Дж. КВт*ч = 3 600 000 Дж", parse_mode=html)),
                current_power=Inf("Мощность тока",
                                  Text("<b>Мощность электрического тока (P)</b> - физическая величина, "
                                       "характеризующая быстроту выполнения работы силами электрического поля. "
                                       "P = U*I. P = [Вт] (ватт)", parse_mode=html)),
                serialСС=Inf("Последовательное СП",
                             Photo('Electrical Phenomena/serial connection.png',
                                   Text("*Последовательное соединение проводников*\n"
                                        "1. При последовательном соединении проводников сила тока в любых частях "
                                        "проводника одна и та же - *I = I₁ = I₂*\n"
                                        "2. При последовательном соединении проводников общее сопротивление цепи"
                                        "равно сумме сопротивления на отдельных участках - *R = R₁ + R₂*\n"
                                        "3. При последовательном соединении проводников полное напряжение, или "
                                        "напряжение на концах проводника, равно сумме напряжений на отдельных "
                                        "участках цепи - *U = U₁ + U₂*"))),
                forward=EducationalData(
                    text="Дальше",
                    data_path=DataPath('physics8', 'electrical_phenomena', 'forward', 'forward'),
                    parallelСС=Inf("Параллельное СП",
                                   Photo('Electrical Phenomena/parallel connection.png',
                                         Text("*Параллельное соединение проводников*\n"
                                              "1. При параллельном соединении проводников сила тока в неразветвленной "
                                              "части цепи равна сумме сил токов в отдельных параллельно соединенных "
                                              "проводниках - *I = I₁ + I₂*\n"
                                              "2. При параллельном соединении проводников сопротивление рассчитывается "
                                              "по формуле: *1/R = 1/R₁ + 1/R₂*\n"
                                              "3. При параллельном соединении проводников напряжение на любом участке и"
                                              " на концах проводника одно и то же - *U = U₁ = U₂*"))),
                    heating=Inf("Нагревание током",
                                Text("Теплота, выделяемая проводником, равна работе тока (Q = A) => <b>Q</b> ="
                                     " U * I * t = <b>I² * R * t</b>\n<b>Закон Джоуля-Ленца</b>\nКоличество "
                                     "теплоты, выделяемое проводником с током, равно произведению квадрата "
                                     "силы тока, сопротивления проводника и времени", parse_mode=html)),
                    short_circuit=Inf("Короткое замыкание",
                                      Photo('Electrical Phenomena/fuse.png',
                                            Text("*Короткое замыкание* - соединение концов участка цепи проводником, "
                                                 "сопротивление которого очень мало по сравнению с сопротивлением "
                                                 "участка цепи\nПредохранители предназначены для отключения линии, если"
                                                 " сита тока вдруг окажется больше допустимой"))),
                    capacitor=Inf("Конденсатор",
                                  Photo('Electrical Phenomena/capacitor.png',
                                        Text("<b>Конденсатор</b> - устройство для накопления заряда.\nЕмкость "
                                             "конденсатора (C) определяется по формуле: <b>C = q/U</b>. C = [Ф] "
                                             "(фарад)\nЭнергия конденсатора (W) рассчитывается по формуле: <b>W = C * "
                                             "U²/2</b>", parse_mode=html)))
                )
            )
        ),
        electromagnetic_phenomena=EducationalData(
            text="Электромагнитные явления",
            data_path=DataPath('physics8', 'electromagnetic_phenomena'),
            magnetic_field=Inf("Магнитное поле",
                               "Магнитная стрелка имеет два полюса: *северный* и *южный*\nМагнитное поле"
                               " существует вокруг любого проводника с током, то есть вокруг движущихся "
                               "электрических зарядов"),
            magnetic_lines=Inf("Магнитные линии",
                               Photo('Electromagnetic Phenomena/magnetic_needles.png',
                                     Text("*Магнитные линии* - линии, вдоль которых в магнитном поле располагаются "
                                          "оси маленьких магнитных стрелок. Они представляют собой замкнутые кривые"
                                          " линии, охватывающие проводник\nСеверный полюс магнита есть направление "
                                          "магнитных линий магнитного поля"))),
            electromagnets=Inf("Электромагниты",
                               Photo('Electromagnetic Phenomena/electromagnet.png',
                                     Text("Катушка с током, состоящая из большого числа витков провода, намотанного"
                                          " на каркас, имеет южный и северный полюс магнитного поля. Такие катушки "
                                          "называют *магнитами*\nМагнитное действие катушки зависит от числа витков"
                                          " провода, силы тока в проводнике. Существует способ усилить силу "
                                          "магнитного взаимодействия, внеся внутрь катушки железный стержень "
                                          "(*сердечник*). *Электромагнит* - катушка с железным сердечником внутри\n"
                                          "Магнитные линии направлены от северного к южному полюсу."))),
            permanent_magnets=Inf("Постоянные магниты",
                                  Photo('Electromagnetic Phenomena/magnetic_needles2.png',
                                        Text("*Магниты* - тела, длительное время сохраняющие намагниченность. "
                                             "Электроны - частицы, создающие магнитное поле. Одноименные полюса "
                                             "магнитной стрелки отталкиваются, а разноименные - притягиваются"))),
            magnetic_field_of_earth=Inf("Магнитное поле Земли",
                                        "Земля имеет магнитное поле. Магнитные полюса не совпадают с "
                                        "географическими полюсами Земли. В некоторых местах из-за других "
                                        "источников магнитного поля существуют магнитные аномалии"),
            effects=Inf("Действия", "Одним из действий магнитного поля является вращение")
        )
    ),
    'chemistry8': EducationalData(
        text=None,
        data_path=DataPath('chemistry8'),
        buttons_row=1,
        concepts_chemistry=EducationalData(
            text="Базовые понятия",
            data_path=DataPath('chemistry8', 'concepts_chemistry'),
            chemistry=Inf("Химия", "*Химия* - наука о веществах, их свойствах и превращениях"),
            substance=Inf("Вещество", "*Вещество* - то, из чего состоит физическое тело"),
            material=Inf("Материал", "*Материал* - вещество или смесь веществ, из которых изготовляются изделия"),
            properties_of_substance=Inf("Свойства вещества",
                                        "*Свойства веществ* - признаки, которыми характеризуется каждое "
                                        "конкретное вещество"),
            observation=Inf("Наблюдение",
                            "*Наблюдение* - концентрация внимания на познаваемых объектах с целью их изучения"),
            experiment=Inf("Химический эксперимент",
                           "*Химический эксперимент* - исследование, которое проводят с веществами "
                           "в контролируемых условиях с целью изучения их свойств"),
            modeling=Inf("Моделирование",
                         "*Моделирование* - изучение объекта с помощью построения и исследования "
                         "моделей\nМодели бывают:\n\t1) материальные\n\t2) знаковые"),
            aggregate_states_of_matter=Inf("Агрегатные состояния вещества",
                                           Photo('Chemistry/TopicSelection/states_of_matter.png',
                                                 Text("Агрегатные состояния вещества:\n\t1) твердое\n\t2) жидкое\n"
                                                      "\t3) газообразное"))),
            mixtures=Inf("Смеси",
                         "*Смесь* - целостная система, состоящая из разнородных компонентов\n"
                         "Смеси бывают:\n\t*Гомогенные*\n\t*Гетерогенные*\n"
                         "Гомогенная смеси - смеси, у которых границы раздела между частицами "
                         "компонентов не видны\nГетерогенная смеси - смеси, у которых границы "
                         "раздела между частицами компонентов видны"),
            methods_of_separation=Inf("Методы разделения смесей",
                                      Photo('Chemistry/TopicSelection/separating_mixture.png')),
            аtomic_and_molecular_teaching=Inf(
                "Атомно-молекулярное учение",
                "*Химический элемент* - определенный вид атомов\n"
                "*Простое вещество* - вещество, образованное атомами одного химического элемента\n"
                "*Сложное вещество* - вещество, образованное атомами нескольких химический элементов\n"
                "_Вода состоит из 2 атомов водорода и 1 атома кислорода, вода - сложное вещество. "
                "Кислород состоит из 2 атомов кислорода, кислород - простое вещество_\n"
                "*Аллотропия* - способность одного химического элемента образовывать несколько простых веществ\n"
                "Атом кислорода способен образовывать несколько простых веществ: кислород и озон. "
                "Такие вещества называются *аллотропными модификациями*\n"
                "*Ион* - положительно или отрицательно заряженная частица, имеющая недостаток или избыток электронов")
        ),
        chemical_formulas_and_reactions=EducationalData(
            text="Химические формулы и реакции",
            data_path=DataPath('chemistry8', 'chemical_formulas_and_reactions'),
            mendeleev_table=Inf("Таблица Менделеева",
                                Photo('Chemistry/main_chemistry_table.png',
                                      Text("Периодическая таблица химических элементов Д. И. Менделеева\n"
                                           "*Период* - горизонтальный ряд элементов. Малые периоды: 1, 2 и 3. "
                                           "Большие периоды: 4, 5 и 6. Незавершенный период - 7\n"
                                           "*Группа* (x8) - вертикальный столбец элементов. Группа делится на *главную*"
                                           " (А) и *побочную* (Б)\n"
                                           "Элементы делятся на *металлы* (Al, Zn, Cu, Au, Hg, Ag и др.) и "
                                           "*неметаллы* (O, C, S, Cl, H, N, P и др.)"))),
            chemical_formulas=Inf("Химические формулы",
                                  "*Химическая формула* - условное обозначение состава вещества с помощью символов "
                                  "хим. элементов и индексов\n"
                                  "CO₂ (цэ-о-два) - один атом углерода (C) и два атома кислорода (O). ₂ - *индекс*, "
                                  "показывает, сколько атомов данного хим. элемента в веществе. 5CO₂ - 5 молекул "
                                  "углекислого газа. 5 - *коэффициент*, показывает количество молекул вещества"),
            atomic_weight=Inf(
                "Атомная масса",
                Text("Атомная масса одного атома водорода равна 1.674*10⁻²⁷ кг. Это масса принята за единицу. "
                     "Относительная атомная масса равна отношению массы атома к данному числу. Относительную "
                     "атомную массу можно найти в таблице Менделеева. Это цифра под порядковым номером элемента."
                     "<b>Относительная атомная масса</b> - Ar(элемент)\n"
                     "Относительную атомную массу <b>всегда</b> округляют до целого числа <b>кроме хлора</b> "
                     "(Ar(Cl) = 35.5)", parse_mode=html)),
            molecular_weight=Inf(
                "Молекулярная масса",
                Text("<b>Относительная молекулярная масса</b> (Mr) равна сумме относительных атомных масс "
                     "входящих в состав вещества атомов с учетом их количества\n"
                     "Mr(H₂O) = 2 * Ar(H) + Ar(O) = 2 * 1 + 16 = 18\n"
                     "В функции /calculate_chemistry есть калькулятор относительной молекулярной массы",
                     parse_mode=html)),
            mass_fraction=Inf(
                "Массовая доля элемента в веществе",
                Text("<b>Массовая доля элемента в веществе (w)</b>\n"
                     "SO₂ w(S) - ?\n"
                     "w(S) = n(S) * Ar(S) / Mr(SO₂) * 100% = 1 * 32 / 64 * 100% = 50%\n"
                     "В функции /calculate_chemistry есть калькулятор массовой доли элемента", parse_mode=html)),
            valence=Inf("Валентность",
                        Text("<b>Валентность</b> - свойство атомов одного химического элемента соединяться со строго "
                             "определенным числом атомов другого химического элемента. Химические элементы делятся на "
                             "элементы с <b>постоянной</b> и <b>переменной</b> валентностью\n"
                             "В функции /task_chemistry есть команда, которая составляет формулы по известным "
                             "химическим элементам", parse_mode=html)),
            chemical_reaction=Inf(
                "Химическая реакция",
                Text("<b>Химическая реакция</b> - химическое явление превращения одних веществ(а) (реагенты) в другие"
                     "веществ(а) (продукты) с новыми свойствами\n"
                     "<b>Уравнение химической реакции</b> - условная запись химической реакции с помощью химических и "
                     "математических знаков\n\n"
                     "Схема химической реакции\n"
                     "P + O₂ -> P₂O₅\n\n"
                     "Уравнение химической реакции\n"
                     "4P + 5O₂ = 2P₂O₅\n\n"
                     "Химические реакции бывают 4 типов\n"
                     "<b>Соединение</b> - хим. реакция, в ходе которой из <b>нескольких</b> простых или сложных веществ "
                     "образуется <b>одно</b> сложное вещество\n"
                     "<b>Разложение</b> - хим. реакция, в ходе которой <b>одно</b> сложное вещество разлагается на "
                     "<b>несколько</b> простых или сложных веществ\n"
                     "<b>Замещение</b> - хим. реакция, в ходе которой из нескольких простых <b>и</b> сложных веществ "
                     "образуются другие простые <b>и</b> сложные вещества\n"
                     "<b>Обмен</b> - хим. реакция, в ходе которой из нескольких <b>сложных</b> веществ образуются "
                     "другие <b>сложные</b> вещества\n"
                     "В функции /task_chemistry есть команда для расставления коэффициентов в уравнении реакции, "
                     "а также определение его типа", parse_mode=html))
        )
    ),
    'calculate_chemistry': EducationalData(
        text=None,
        data_path=DataPath('calculate_chemistry'),
        buttons_row=1,
        molecular_weight=EducationalFunction(
            text="Mr (относительная молекулярная масса)",
            data_path=DataPath('calculate_chemistry', 'molecular_weight'),
            state=UserState.molecular_weight,
            function=answer_text("Напишите формулу вещества. Например, `H2O`")
        ),
        mass_fraction=EducationalFunction(
            text="ω (массовая доля элемента в веществе)",
            data_path=DataPath('calculate_chemistry', 'mass_fraction'),
            state=UserState.mass_fraction1,
            function=answer_text("Отправьте формулу вещества, в котором нужно посчитать массовую долю какого-либо "
                                 "элемента. Например: `H2O`")
        ),
        volume_fraction=EducationalFunction(
            text="φ (объемная доля компонентов газовой смеси)",
            data_path=DataPath('calculate_chemistry', 'volume_fraction'),
            state=UserState.volume_fraction1,
            function=answer_text("Отправьте мне объем газовой смеси с указанием единиц измерения. "
                                 "Например: `3л` или `3м³`")
        ),
        amount_of_substance_from_mass=EducationalFunction(
            text="n (количество вещества через массу)",
            data_path=DataPath('calculate_chemistry', 'amount_of_substance_from_mass'),
            state=UserState.amount_of_substance_from_mass1,
            function=answer_text("Отправьте массу вещества с указанием единиц измерения. "
                                 "Например: `5г` или `5кг`")
        ),
        amount_of_substance_from_number_of_particles=EducationalFunction(
            text="n (количество вещества через число частиц)",
            data_path=DataPath('calculate_chemistry', 'amount_of_substance_from_number_of_particles'),
            state=UserState.amount_of_substance_from_number_of_particles,
            function=answer_text("Отправьте число частиц вещества. Для знака степени используйте `**`. "
                                 "Например: `6.02 * 10**23`")
        ),
        amount_of_substance_from_volume_of_gas=EducationalFunction(
            text="n (количество вещества через объем газа)",
            data_path=DataPath('calculate_chemistry', 'amount_of_substance_from_volume_of_gas'),
            state=UserState.amount_of_substance_from_volume_of_gas,
            function=answer_text("Отправьте мне объем *газа* с указанием единиц измерения. "
                                 "Например: `3л` или `3м³`")
        ),
        gas_density=EducationalFunction(
            text="ρ (плотность газа через его формулу)",
            data_path=DataPath('calculate_chemistry', 'gas_density'),
            state=UserState.gas_density,
            function=answer_text("Отправьте мне формулу *газа*. Например: `CO2`")
        )
    ),
    'task_chemistry': EducationalData(
        text=None,
        data_path=DataPath('task_chemistry'),
        buttons_row=1,
        formulation_of_chemical_formulas=EducationalFunction(
            text="Составление формул по известным хим. элементам",
            data_path=DataPath('task_chemistry', 'formulation_of_chemical_formulas'),
            state=UserState.formulation_of_chemical_formulas,
            function=answer_text("Отправьте формулу вещества, в котором необходимо расставить "
                                 "индексы. Например: `HO`")
        ),
        making_formulas_by_name=EducationalFunction(
            text="Составление формул по названию вещества",
            data_path=DataPath('task_chemistry', 'making_formulas_by_name'),
            state=UserState.making_formulas_by_name,
            function=answer_text("Отправьте мне название вещества, я составлю его формулу. Например: "
                                 "`хлорид натрия`, `кислород`, `соляная кислота` или `хлороводород`")
        ),
        setting_coefficients=EducationalFunction(
            text="Расставление коэффициентов в хим реакции",
            data_path=DataPath('task_chemistry', 'setting_coefficients'),
            state=UserState.setting_coefficients,
            function=answer_text("Отправьте уравнение реакции, в которой необходимо расставить "
                                 "коэффициенты. Например: `C + O2 = CO2`")
        )
    )
}
