import asyncio
import json
import random
from websockets import serve
import logging
import requests
import secrets

# 配置信息
list_server = ''
blacklist_url = f"{list_server}/blacklist.txt"  # 新增黑名单URL配置
# 在全局配置部分添加 ntfy 配置项
ntfy_url = ""  # 可在配置文件中设置 ntfy 的 URL，为空则不提醒掉线
# groups.txt中设置你有管理员的群号，一行一个，必须是utf-8编码

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 文件处理器
file_handler = logging.FileHandler('onebot_client.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 控制台处理器
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# 在全局变量区域新增
current_blacklist = []  # 存储内存中的黑名单

async def fetch_blacklist():
    """从服务器拉取黑名单文件"""
    global current_blacklist
    try:
        response = requests.get(blacklist_url, timeout=10)
        response.raise_for_status()
        
        # 直接更新内存中的黑名单
        current_blacklist = [line.strip() for line in response.text.split('\n') if line.strip()]
        logging.info("成功更新内存黑名单")
        
    except Exception as e:
        logging.error(f"拉取黑名单失败: {str(e)}")
        raise

async def scheduled_sync():
    """定时同步任务"""
    while True:
        await asyncio.sleep(6 * 3600)  # 6小时间隔
        try:
            await fetch_blacklist()
        except Exception as e:
            logging.error(f"定时同步黑名单失败: {str(e)}")

def load_groups():
    """加载允许处理的群号列表"""
    try:
        with open('groups.txt', 'r', encoding='utf-8-sig') as f:
            return [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        logging.warning("未找到 groups.txt 文件")
        return []


# 新增全局变量，用于记录连续掉线的心跳包次数
consecutive_offline_count = 0

async def handle_message(event):
    global consecutive_offline_count
    """处理OneBot事件"""
    post_type = event.get('post_type')
    meta_event_type = event.get('meta_event_type')
    if post_type == 'meta_event' and meta_event_type in ['lifecycle', 'heartbeat']:
        if meta_event_type == 'lifecycle':
            sub_type = event.get('sub_type')
            if sub_type == 'connect':
                self_id = event.get('self_id')
                if self_id:
                    logging.info(f"self_id {self_id} 已连接到中间件")
                else:
                    logging.warning("收到生命周期连接消息，但未包含 self_id")
            else:
                logging.info(f"收到生命周期消息: {event}")
        elif meta_event_type == 'heartbeat':
            logging.info(f"收到心跳消息: {event}")
            status = event.get('status', {})
            online = status.get('online', True)
            self_id = event.get('self_id')
            if not online:
                consecutive_offline_count += 1
                logging.critical(f"self_id {self_id} QQ 掉线，心跳检测 online 为 False，连续掉线次数: {consecutive_offline_count}")
                if ntfy_url:
                    try:
                        message = f"self_id {self_id} QQ 掉线，心跳检测 online 为 False，连续掉线次数: {consecutive_offline_count}"
                        requests.post(ntfy_url, data=message.encode(encoding='utf-8'), verify=False)
                        logging.info(f"已通过 ntfy 发送 QQ 掉线通知到 {ntfy_url}")
                    except Exception as e:
                        logging.error(f"通过 ntfy 发送通知失败: {str(e)}")
                if consecutive_offline_count >= 2:
                    logging.critical("连续两次心跳包显示掉线，程序将结束运行。")
                    raise SystemExit  # 终止程序
            else:
                # 如果当前心跳包显示在线，将连续掉线次数重置为 0
                consecutive_offline_count = 0
            return None

    if not all(key in event for key in ['post_type', 'notice_type']):
        logging.warning(f"收到无效事件格式：{event}")
        return None

    groups = load_groups()
    
    if event.get('post_type') == 'notice' and event.get('notice_type') == 'group_increase':
        user_id = event['user_id']
        group_id = event['group_id']
        if str(group_id) not in groups:
            return None

        sub_type = event.get('sub_type', 'approve')
        operator_id = event.get('operator_id', 0)
        
        try:
            # 替换本地文件读取为内存读取
            if str(user_id) in current_blacklist:
                logging.info(
                    f"黑名单成员 {user_id} 通过 {sub_type} 方式加入群 {group_id}，"
                    f"操作者：{operator_id}"
                )
                
                predefined_messages = [
                    "您好呀，这个群可能不太适合您长留呢，祝您在其他地方找到更多乐趣。",
                    "欢迎短暂来到我们群，不过这里或许不是您的最佳归属，祝您有好的旅程。",
                    "看来您不小心来到了我们的小天地，这里可能不太符合您的需求哦。",
                    "嘿，朋友，这个群可能和您有点“气场不合”，去别处看看吧。",
                    "您来到我们群啦，不过这里可能没有您期待的内容，祝您一切顺利。",
                    "温馨提示，这个群不太能满足您，希望您能找到更合适的地方。",
                    "您好，本群可能不是您理想的交流地，祝您在其他群玩得开心。",
                    "欢迎光临，但我们群可能和您的兴趣不太匹配，祝您有好的体验。",
                    "哎呀，您误进我们群啦，去更适合您的地方说不定会更好。",
                    "您来到我们群啦，不过可能这里不是您的“主场”，祝您生活愉快。",
                    "嘿，这里可能不是您要找的群，祝您在其他地方收获满满。",
                    "本群也许和您的节奏不太一样，希望您能找到合拍的群体。",
                    "您好，这个群可能无法给您想要的，去别处找找说不定有惊喜。",
                    "欢迎到我们群转了一圈，不过这里可能不是您的长久之选。",
                    "看来您和我们群的缘分有点浅，祝您在其他地方一切都好。",
                    "您来到这个群啦，可惜可能不太对您的“胃口”，祝您顺心如意。",
                    "嘿，朋友，这个群不太适合您，去寻找更契合您的群吧。",
                    "温馨告知，这里可能不是您的理想群聊，祝您找到合适的。",
                    "您好，本群可能满足不了您的需求，祝您在其他群里畅聊。",
                    "哎呀，您来错群啦，去更适合您的群里开启新的交流吧。"
                ]
                
                try:
                    msg_delay = secrets.randbelow(2001) / 1000 + 1
                    await asyncio.sleep(msg_delay)
                    
                    msg_response = requests.post(
                        'http://localhost:3000/send_group_msg',
                        json={
                            'group_id': group_id,
                            'message': [{
                                "type": "at",
                                "data": {"qq": f"{user_id}", "name": f"{user_id}"}
                                }, {
                                'type': 'text',
                                'data': {'text': ' ' + secrets.choice(predefined_messages)}
                            }]
                        }
                    )
                    
                    kick_delay = secrets.randbelow(501) / 1000 + 0.5
                    await asyncio.sleep(kick_delay)
                    
                    kick_response = requests.post(
                        'http://localhost:3000/set_group_kick',
                        json={'group_id': group_id, 'user_id': user_id}
                    )
                    
                    if msg_response.status_code != 200:
                        logging.error(f"发送消息失败: {msg_response.text}")
                    if kick_response.status_code != 200:
                        logging.error(f"踢出失败: {kick_response.text}")

                    return [
                        {"status_code": msg_response.status_code, "text": msg_response.text},
                        {"status_code": kick_response.status_code, "text": kick_response.text}
                    ]
                except Exception as e:
                    logging.error(f"操作执行失败: {str(e)}")

        except FileNotFoundError:
            logging.warning("未找到 blacklist.txt 文件")

    elif event.get('post_type') == 'message' and event.get('message_type') == 'group':
        if 'group_id' not in event:
            return None
        if str(event['group_id']) not in groups:
            return None

    return None

async def websocket_handler(websocket):
    async for message in websocket:
        try:
            event = json.loads(message)
            if response := await handle_message(event):
                await websocket.send(json.dumps(response))
        except json.JSONDecodeError:
            logging.error(f"无效的JSON数据：{message}")

async def startup_scan():
    """启动时扫描所有已加入群的成员"""
    logging.info("开始执行启动扫描任务")
    
    groups = load_groups()
    try:
        # 直接使用内存中的黑名单
        blacklist = current_blacklist
    except Exception as e:
        logging.error(f"黑名单数据异常: {str(e)}")
        return

    try:
        group_list_res = requests.post('http://localhost:3000/get_group_list')
        if group_list_res.status_code != 200:
            logging.error(f"获取群列表失败: {group_list_res.text}")
            return

        allowed_groups = [
            int(g['group_id']) for g in group_list_res.json().get('data', [])
            if str(g['group_id']) in groups
        ]

        for group_id in allowed_groups:
            member_res = requests.post(
                'http://localhost:3000/get_group_member_list',
                json={'group_id': group_id}
            )
            if member_res.status_code != 200:
                logging.error(f"获取群{group_id}成员失败: {member_res.text}")
                continue

            for member in member_res.json().get('data', []):
                user_id = str(member.get('user_id', ''))
                if user_id in blacklist:
                    kick_res = requests.post(
                        'http://localhost:3000/set_group_kick',
                        json={'group_id': group_id, 'user_id': user_id}
                    )
                    if kick_res.status_code == 200:
                        logging.info(f"启动扫描踢出黑名单用户 {user_id}（群 {group_id}）")
                    else:
                        logging.error(f"踢出失败: {kick_res.text}")

    except Exception as e:
        logging.error(f"启动扫描出错: {str(e)}")

async def main():
    try:
        # 启动时首次同步
        await fetch_blacklist()
    except Exception:
        logging.critical("启动时黑名单同步失败，程序终止")
        raise SystemExit  # 终止程序
    # 启动定时任务
    scheduled_task = asyncio.create_task(scheduled_sync())
    # 启动扫描任务
    await startup_scan()
    # 启动WebSocket服务器
    server = await serve(websocket_handler, "0.0.0.0", 6700)
    try:
        logging.info("程序已启动，按 Ctrl - C 停止程序")
        await server.wait_closed()
    except KeyboardInterrupt:
        logging.info("收到 Ctrl - C 信号，正在停止程序...")
        # 取消定时任务
        scheduled_task.cancel()
        try:
            await scheduled_task
        except asyncio.CancelledError:
            logging.info("定时任务已取消")
        # 关闭WebSocket服务器
        server.close()
        await server.wait_closed()
        logging.info("WebSocket服务器已关闭，程序已停止")
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())