import os
import sys
from pathlib import Path

import pandas as pd

import Guest_Class
import Food_Class

# 把工作目录切换到当前 .py 文件所在目录
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

Flag = True
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

# ✅ 用 Path 处理上一级目录里的 Excel（避免 \ 转义问题）
xlsx_path = (BASE_DIR.parent.parent / "东方夜雀食堂.xlsx")

Normal_Guest_Dict = {}
Rare_Guest_Dict = {}
Food_Dict = {}
Drink_Dict = {}
Ingredient_Dict = {}

all_dict = {
    "普客": Normal_Guest_Dict,
    "稀客": Rare_Guest_Dict,
    "料理": Food_Dict,
    "酒水": Drink_Dict,
    "食材": Ingredient_Dict,
}


def split_safe(x, sep="、"):
    """Excel 空值/NaN 防护的 split：返回 list[str]"""
    if x is None:
        return []
    try:
        if x != x:  # NaN
            return []
    except Exception:
        pass

    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return []
    return [p.strip() for p in s.split(sep) if p.strip()]


def init_all_class(Dict, sheet_name, sheet: pd.DataFrame):
    for row in sheet.index:
        if sheet_name == "料理":
            thing = Food_Class.Food(sheet.loc[row])
            Dict[thing.name] = thing
        elif sheet_name == "酒水":
            thing = Food_Class.Drink(sheet.loc[row])
            Dict[thing.name] = thing
        elif sheet_name == "食材":
            thing = Food_Class.Ingredient(sheet.loc[row])
            Dict[thing.name] = thing
        else:
            thing = Guest_Class.Guest(sheet.loc[row])
            Dict[thing.name] = thing


def find_food(guest_list, hate_tag, tag_count):
    recommend_dict = {}
    for food in Food_Dict.values():
        count = 0
        for guest in guest_list:
            if food.checkbyprops(guest.preferred_tags) >= tag_count or "全部" in guest.preferred_tags:
                count += 1
        if count > 0:
            recommend_dict[food.name] = [food, count]

    remove_list = []
    for recommend in list(recommend_dict.keys()):
        if hate_tag and recommend_dict[recommend][0].checkbyprops([hate_tag]):
            remove_list.append(recommend)

    for remove in remove_list:
        recommend_dict.pop(remove, None)

    return recommend_dict


def find_drink(guest_list, tag_count):
    recommend_dict = {}
    for drink in Drink_Dict.values():
        count = 0
        for guest in guest_list:
            if drink.checkbyprops(guest.beverage_tags) >= tag_count or "全部" in guest.beverage_tags:
                count += 1
        if count > 0:
            recommend_dict[drink.name] = [drink, count]
    return recommend_dict


def print_df(df, num, flag=False):
    try:
        while num != "":
            print(df.head(int(num)).to_string(index=flag))
            num = input("输入大于" + num + "的数字以查看后续排行(或回车返回主菜单)：")
    except ValueError:
        pass


def get_place_and_tagcoutn(place_list):
    try:
        place = input("请选择地点:")
        while place == "":
            place = input()
        while int(place) < 1:
            print("数字过小,请重新输入:", end="")
            place = input()
        place = place_list[int(place) - 1]

        tag_count = input("输入tag重叠数：")
        while tag_count == "":
            tag_count = input()
        while int(tag_count) < 1:
            print("数字过小,请重新输入:", end="")
            tag_count = input()

        tag_count = int(tag_count)
        print(place)
        return place, tag_count

    except ValueError as e:
        print(repr(e))
        input("输入有误(可能非数字)，回车后重新输入")
        return get_place_and_tagcoutn(place_list)

    except IndexError as e:
        print(repr(e))
        input("输入有误(可能超出地点数量)，回车后重新输入")
        return get_place_and_tagcoutn(place_list)


def max_tag_food(guest, Food_Dict):
    recommend_dict = {}
    key = None
    for food in Food_Dict.values():
        tag_num = guest.checkbyfav(food.tags)
        if recommend_dict == {}:
            recommend_dict[food.name] = tag_num
            key = food.name
        elif recommend_dict[key] == tag_num:
            recommend_dict[food.name] = tag_num
        elif recommend_dict[key] < tag_num:
            recommend_dict.clear()
            recommend_dict[food.name] = tag_num
            key = food.name
    return recommend_dict


print("实例化数据中，请稍后...")

# ✅ 只读取需要的 5 张表，避免读到 icon_map/迁移报告/merchant_data 等导致 KeyError
NEEDED_SHEETS = list(all_dict.keys())
sheet_list = pd.read_excel(xlsx_path, sheet_name=NEEDED_SHEETS)

# 先实例化对象
for sheet_name, df in sheet_list.items():
    init_all_class(all_dict[sheet_name], sheet_name, df)

# ✅ 构造 place_list：对 NaN 做防护（表头模糊匹配：Spawn Areas / 出没地区）
place_set = set()
if "普客" in sheet_list:
    df_ng = sheet_list["普客"]
    col_spawn = Food_Class.find_df_col(df_ng, ["Spawn Areas", "出没地区", "distanceList"])
    if col_spawn:
        for distance in df_ng.loc[:, col_spawn]:
            place_set.update(split_safe(distance, "、"))
place_list = list(place_set)

# 料理补充计算成本/利润
for food in Food_Dict.values():
    food.after_init(Ingredient_Dict)

os.system("cls")

while Flag:
    print(
        "1.根据地点推荐食谱\n"
        "2.根据地点推荐酒水\n"
        "3.酒水查询\n"
        "4.流行菜单利润表\n"
        "5.怪诞料理模式\n"
        "6.显示所有料理售价和实际利润\n"
        "7.显示所有酒水售价和实际利润\n"
        "0.退出程序"
    )

    n = input("输入序号并回车：")
    while n not in ["0", "1", "2", "3", "4", "5", "6", "7"]:
        n = input()

    if n == "0":
        Flag = False
        sys.exit()

    if n == "1" or n == "2":
        for p in range(len(place_list)):
            print(p + 1, place_list[p])

        place, tag_count = get_place_and_tagcoutn(place_list)

        guest_list = []
        for guest in Normal_Guest_Dict.values():
            if guest.checkbydistanceList(place):
                guest_list.append(guest)

        if n == "1":
            hate_tag = input("输入厌恶标签(无则回车)：")
            recommend_dict = find_food(guest_list, hate_tag, tag_count)

            name_list = []
            guestcount_list = []
            price_list = []
            cost_list = []
            cost_actual_list = []
            profit_list = []
            profit_actual_list = []
            sort_count = []

            for food in recommend_dict.values():
                name_list.append(food[0].name)
                guest_count = food[1]
                guestcount_list.append(guest_count)
                price_list.append(food[0].sell_price)
                cost_list.append(food[0].cost)
                cost_actual_list.append(food[0].cost_actual)
                profit_list.append(food[0].profit)
                profit_actual_list.append(food[0].profit_actual)

                # 防 0 除
                denom = food[0].cost_actual if food[0].cost_actual != 0 else 1
                ratio = food[0].sell_price / denom
                if ratio > 5:
                    ratio = 5
                sort_count.append(float("%.2f" % (guest_count + ratio)))

            df = pd.DataFrame(
                {
                    "名称": name_list,
                    "顾客数(tag≥" + str(tag_count) + ")": guestcount_list,
                    "售价": price_list,
                    "成本": cost_list,
                    "实际成本": cost_actual_list,
                    "利润": profit_list,
                    "实际利润": profit_actual_list,
                    "推荐指数": sort_count,
                }
            )
            df = df.sort_values(
                by=["顾客数(tag≥" + str(tag_count) + ")", "推荐指数", "实际利润"],
                ascending=[False, False, False],
            )

        elif n == "2":
            recommend_dict = find_drink(guest_list, tag_count)

            name_list = []
            guestcount_list = []
            price_list = []
            profit_list = []
            sort_count = []

            for drink in recommend_dict.values():
                name_list.append(drink[0].name)
                guest_count = drink[1]
                guestcount_list.append(guest_count)
                price_list.append(drink[0].sell_price)
                profit_list.append(drink[0].profit)

                denom = drink[0].buy_price if drink[0].buy_price != 0 else 1
                sort_count.append("%.2f" % (guest_count + (drink[0].sell_price / denom)))

            df = pd.DataFrame(
                {
                    "名称": name_list,
                    "顾客数(tag≥" + str(tag_count) + ")": guestcount_list,
                    "售价": price_list,
                    "利润": profit_list,
                    "推荐指数": sort_count,
                }
            )
            df = df.sort_values(
                by=["顾客数(tag≥" + str(tag_count) + ")", "推荐指数", "利润"],
                ascending=[False, False, False],
            )

        if not df.empty:
            print_df(df, "20")
        else:
            input("获得结果为空(回车返回主菜单)")

    elif n == "3":
        select_tag = input(r'输入查询的标签(多个标签请"、"隔开)：')
        while select_tag == "":
            select_tag = input()
        select_tag = select_tag.split("、")

        recommend_list = []
        for drink in Drink_Dict.values():
            if drink.checkbyprops(select_tag):
                recommend_list.append(drink)

        df = pd.DataFrame(
            {
                "名称": [drink.name for drink in recommend_list],
                "售价": [drink.sell_price for drink in recommend_list],
                "利润": [drink.profit for drink in recommend_list],
            }
        )
        df = df.sort_values(by="利润", ascending=False)

        if not df.empty:
            print_df(df, "20")
        else:
            input("获得结果为空(回车返回主菜单)")

    elif n == "4":
        popular_tag = input("输入流行标签：")
        while popular_tag == "":
            popular_tag = input()

        recommend_list = []
        for food in Food_Dict.values():
            if food.checkbyprops([popular_tag]):
                recommend_list.append(food)

        df = pd.DataFrame(
            {
                "名称": [food.name for food in recommend_list],
                "售价": [food.sell_price for food in recommend_list],
                "实际利润": [food.profit_actual for food in recommend_list],
            }
        )
        df = df.sort_values(by="实际利润", ascending=False)

        if not df.empty:
            print_df(df, "20")
        else:
            input("获得结果为空(回车返回主菜单)")

    elif n == "5":
        recommend_dict = {}
        pd_dict = {}

        for guest in Normal_Guest_Dict.values():
            recommend_dict[guest.name] = max_tag_food(guest, Food_Dict)

        for k, v in recommend_dict.items():
            pd_dict[k] = pd.DataFrame([v.values(), [Food_Dict[n].profit_actual for n in v.keys()]])
            pd_dict[k].index = ["重合数", "实际利润"]
            pd_dict[k].columns = v.keys()

        print("数据处理完成")
        guest_name = input("请输入顾客名(回车返回主菜单)：")

        while guest_name != "":
            try:
                print(guest_name)
                print(pd_dict[guest_name].to_string() + "\n")
            except KeyError:
                print("顾客名错误，请重新输入")
            guest_name = input("请输入顾客名(回车返回主菜单)：")

    elif n == "6":
        df = pd.DataFrame(
            {
                "名称": [food.name for food in Food_Dict.values()],
                "售价": [food.sell_price for food in Food_Dict.values()],
                "实际利润": [food.profit_actual for food in Food_Dict.values()],
            }
        )
        df = df.sort_values(by="实际利润", ascending=False)

        if not df.empty:
            print(df.to_string(index=False))
        else:
            input("获得结果为空(回车返回主菜单)")

    elif n == "7":
        df = pd.DataFrame(
            {
                "名称": [drink.name for drink in Drink_Dict.values()],
                "售价": [drink.sell_price for drink in Drink_Dict.values()],
                "实际利润": [drink.profit for drink in Drink_Dict.values()],
            }
        )
        df = df.sort_values(by="实际利润", ascending=False)

        if not df.empty:
            print(df.to_string(index=False))
        else:
            input("获得结果为空(回车返回主菜单)")
