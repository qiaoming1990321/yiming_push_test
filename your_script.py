#!/usr/bin/env python3
import requests
import json
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FactoryMonitor:
    def __init__(self):
        self.base_url = "http://159.75.99.78:80"
        self.feishu_webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/ceb6a186-997a-4023-91b9-f3f1934433dd"
        self.username = "admin"
        self.pwd = "911111"
        self.token = ""
        self.user_id = ""
        self.headers = {}

    def login(self):
        """1. 请求登录接口"""
        url = f"{self.base_url}/admin-api/v1/app/user/login"
        payload = {"username": self.username, "pwd": self.pwd}
        try:
            response = requests.post(url, json=payload)
            res_data = response.json()
            # 兼容性处理：取 data 里的数据
            data = res_data.get("data", {})
            self.token = data.get("token")
            self.user_id = data.get("userId")
            
            if self.token:
                self.headers = {
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                }
                logging.info(f"登录成功: userId={self.user_id}")
                return True
            else:
                logging.error(f"登录失败，未获取到token: {res_data}")
                return False
        except Exception as e:
            logging.error(f"登录异常: {e}")
            return False

    def get_factory_list(self):
        """2. 请求工厂列表接口并保存数据"""
        url = f"{self.base_url}/admin-api/v1/app/factory/list"
        params = {"userId": self.user_id, "token": self.token}
        try:
            response = requests.post(url, json=params, headers=self.headers)
            res_data = response.json()
            with open("factory_list.json", "w", encoding="utf-8") as f:
                json.dump(res_data, f, ensure_ascii=False, indent=4)
            logging.info(res_data)
#            logging.info("工厂列表已保存")
            return res_data.get("data", [])
        except Exception as e:
            logging.error(f"获取工厂列表异常: {e}")
            return []

    def query_inventory(self):
        """3. 请求库存接口"""
        url = f"{self.base_url}/admin-api/v1/app/factory/queryInventoryByFactory"
        params = {"userId": self.user_id, "token": self.token}
        try:
            response = requests.post(url, json=params, headers=self.headers)
            res_data = response.json()
#            logging.info(res_data)
            return res_data.get("data", [])
        except Exception as e:
            logging.error(f"查询库存异常: {e}")
            return []

    def process_and_push(self, inventory_data):
        """4. 解析嵌套结构并按工厂维度推送"""
        if not inventory_data:
            logging.info("没有库存数据需要推送")
            return

        for factory in inventory_data:
            factory_name = factory.get("factoryName", "未知工厂")
            factory_id = factory.get("factoryId", "未知ID")
            
            # 构建单条飞书消息内容
            msg_lines = []
            msg_lines.append(f"🏭 工厂: {factory_name}")
            msg_lines.append("-" * 30)

            case_numbers = factory.get("caseNumbers", [])
            if not case_numbers:
                continue

            for case in case_numbers:
                case_name = case.get("caseNumberName", "未知案号")
                msg_lines.append(f"📁 案号: {case_name}")
                
                products = case.get("products", [])
                for prod in products:
                    prod_name = prod.get("productName", "未知产品")
                    msg_lines.append(f"  🔹 产品名称: {prod_name}")
                    
                    # 遍历 productNums (列表里的字典)
                    product_nums = prod.get("productNums", [])
                    for num_dict in product_nums:
                        for key, value in num_dict.items():
                            msg_lines.append(f"    ▫️ 剩余: {key}: {value}")
            
            # 发送当前工厂的消息
            self.send_to_feishu("\n".join(msg_lines))

    def send_to_feishu(self, content):
        """5. 飞书推送"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        try:
            resp = requests.post(self.feishu_webhook, json=payload)
            if resp.status_code == 200:
                logging.info("飞书消息发送成功")
            else:
                logging.error(f"飞书发送失败: {resp.text}")
        except Exception as e:
            logging.error(f"推送异常: {e}")

    def run(self):
        if self.login():
            # 获取工厂列表保存
            self.get_factory_list()
            # 获取库存
            inventory = self.query_inventory()
            # 分工厂推送
            self.process_and_push(inventory)

if __name__ == "__main__":
    monitor = FactoryMonitor()
    monitor.run()
