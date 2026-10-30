// Generated from data/demo.json by tools/sync_demo.py.
window.MYSTIA_DEMO_DATA = {
  "format": "mystia-planner-data/v1",
  "metadata": {
    "title": "合成餐馆样例",
    "kind": "synthetic",
    "description": "为演示规则与供给取舍人工编写；人物、配方、价格、供给均为虚构，不是游戏攻略。",
    "provenance": "Created for this portfolio during AI-assisted project cleanup.",
    "price_semantics": "Fictional expected acquisition prices; no empirical claim."
  },
  "sheets": {
    "食材": [
      {
        "Name": "谷物",
        "Tags": "饱腹",
        "Buy Price": 2,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "豆腐",
        "Tags": "素、清淡",
        "Buy Price": 3,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "蘑菇",
        "Tags": "鲜、素",
        "Buy Price": 4,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "竹笋",
        "Tags": "鲜、素",
        "Buy Price": 5,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "苹果",
        "Tags": "甜、果味",
        "Buy Price": 3,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "蜂蜜",
        "Tags": "甜、果味",
        "Buy Price": 5,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "香草",
        "Tags": "香、清淡",
        "Buy Price": 2,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "豆子",
        "Tags": "饱腹、素",
        "Buy Price": 2,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "芝麻",
        "Tags": "香、和风",
        "Buy Price": 3,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "椒盐",
        "Tags": "咸、重油",
        "Buy Price": 2,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "肉片",
        "Tags": "肉、鲜",
        "Buy Price": 8,
        "Owned": 1,
        "Level": 1
      },
      {
        "Name": "豆乳",
        "Tags": "甜、清淡",
        "Buy Price": 4,
        "Owned": 1,
        "Level": 1
      }
    ],
    "料理": [
      {
        "Name": "家常饭",
        "Cookware": "料理台",
        "Sell Price": 6,
        "Tags": "素、家常、饱腹、和风",
        "Required Ingredients": "谷物",
        "Forbidden Ingredients": "",
        "Owned": 1
      },
      {
        "Name": "菜汤",
        "Cookware": "煮锅",
        "Sell Price": 12,
        "Tags": "素、清淡、汤羹",
        "Required Ingredients": "豆腐",
        "Forbidden Ingredients": "肉、重油",
        "Owned": 1
      },
      {
        "Name": "烤串",
        "Cookware": "烧烤架",
        "Sell Price": 30,
        "Tags": "肉、香、下酒",
        "Required Ingredients": "肉片",
        "Forbidden Ingredients": "甜",
        "Owned": 1
      },
      {
        "Name": "蒸团",
        "Cookware": "蒸锅",
        "Sell Price": 24,
        "Tags": "素、甜、和风",
        "Required Ingredients": "谷物、苹果",
        "Forbidden Ingredients": "咸",
        "Owned": 1
      },
      {
        "Name": "煎饼",
        "Cookware": "油锅",
        "Sell Price": 40,
        "Tags": "家常、重油、咸",
        "Required Ingredients": "谷物、芝麻",
        "Forbidden Ingredients": "",
        "Owned": 1
      },
      {
        "Name": "果盘",
        "Cookware": "料理台",
        "Sell Price": 18,
        "Tags": "素、甜、果味、小巧",
        "Required Ingredients": "苹果",
        "Forbidden Ingredients": "肉、水产",
        "Owned": 1
      },
      {
        "Name": "香菇汤",
        "Cookware": "煮锅",
        "Sell Price": 65,
        "Tags": "素、鲜、清淡、汤羹",
        "Required Ingredients": "蘑菇、竹笋",
        "Forbidden Ingredients": "",
        "Owned": 1
      },
      {
        "Name": "试作拼盘",
        "Cookware": "料理台",
        "Sell Price": 75,
        "Tags": "肉、鲜、香、家常",
        "Required Ingredients": "谷物、蘑菇、肉片、芝麻、香草",
        "Forbidden Ingredients": "",
        "Owned": 1
      }
    ],
    "稀客": [
      {
        "Name": "旅人",
        "Type": "rare",
        "Preferred Tags": "家常、饱腹、实惠、料理台、流行·喜爱",
        "Disliked Tags": "重油",
        "Budget": "30–60",
        "Spawn Areas": "合成演示区",
        "Beverage Tags": ""
      },
      {
        "Name": "茶客",
        "Type": "rare",
        "Preferred Tags": "素、清淡、甜、和风、流行·喜爱",
        "Disliked Tags": "肉、咸",
        "Budget": "40–80",
        "Spawn Areas": "合成演示区",
        "Beverage Tags": ""
      },
      {
        "Name": "匠人",
        "Type": "rare",
        "Preferred Tags": "肉、香、下酒、烧烤架、流行·喜爱",
        "Disliked Tags": "甜、流行·厌恶",
        "Budget": "50–100",
        "Spawn Areas": "合成演示区",
        "Beverage Tags": ""
      }
    ],
    "食材merchant_data": [
      {
        "Name": "谷物",
        "Total Daily Quantity": 36,
        "commission": 0,
        "Buy Price1": 2,
        "Daily Quantity1": 36,
        "Average Buy Price": 2
      },
      {
        "Name": "豆腐",
        "Total Daily Quantity": 26,
        "commission": 0,
        "Buy Price1": 3,
        "Daily Quantity1": 26,
        "Average Buy Price": 3
      },
      {
        "Name": "蘑菇",
        "Total Daily Quantity": 18,
        "commission": 0,
        "Buy Price1": 4,
        "Daily Quantity1": 18,
        "Average Buy Price": 4
      },
      {
        "Name": "竹笋",
        "Total Daily Quantity": 12,
        "commission": 0,
        "Buy Price1": 5,
        "Daily Quantity1": 12,
        "Average Buy Price": 5
      },
      {
        "Name": "苹果",
        "Total Daily Quantity": 24,
        "commission": 0,
        "Buy Price1": 3,
        "Daily Quantity1": 24,
        "Average Buy Price": 3
      },
      {
        "Name": "蜂蜜",
        "Total Daily Quantity": 9,
        "commission": 0,
        "Buy Price1": 5,
        "Daily Quantity1": 9,
        "Average Buy Price": 5
      },
      {
        "Name": "香草",
        "Total Daily Quantity": 20,
        "commission": 0,
        "Buy Price1": 2,
        "Daily Quantity1": 20,
        "Average Buy Price": 2
      },
      {
        "Name": "豆子",
        "Total Daily Quantity": 30,
        "commission": 0,
        "Buy Price1": 2,
        "Daily Quantity1": 30,
        "Average Buy Price": 2
      },
      {
        "Name": "芝麻",
        "Total Daily Quantity": 16,
        "commission": 0,
        "Buy Price1": 3,
        "Daily Quantity1": 16,
        "Average Buy Price": 3
      },
      {
        "Name": "椒盐",
        "Total Daily Quantity": 22,
        "commission": 0,
        "Buy Price1": 2,
        "Daily Quantity1": 22,
        "Average Buy Price": 2
      },
      {
        "Name": "肉片",
        "Total Daily Quantity": 14,
        "commission": 0,
        "Buy Price1": 8,
        "Daily Quantity1": 14,
        "Average Buy Price": 8
      },
      {
        "Name": "豆乳",
        "Total Daily Quantity": 21,
        "commission": 0,
        "Buy Price1": 4,
        "Daily Quantity1": 21,
        "Average Buy Price": 4
      }
    ]
  }
};
