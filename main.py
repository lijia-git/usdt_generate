import hashlib
import time
import mnemonic
import pyopencl as cl
import numpy as np
from tronpy import Tron
from tronpy.keys import PrivateKey
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import secrets

class USDTAddressGenerator:
    def __init__(self, platform_index=None, device_index=None, mode='mnemonic'):
        self.client = Tron()
        self.found_addresses = []
        self.total_generated = 0
        self.last_time = None
        self.last_count = 0
        self.running = False
        self.mode = mode  # 'mnemonic' 或 'privatekey'
        
        # 初始化OpenCL
        self.init_gpu(platform_index, device_index)
        
        # 创建速度统计线程，但不立即启动
        self.speed_thread = threading.Thread(target=self._print_speed)
        self.speed_thread.daemon = True

    def list_gpu_devices(self):
        """列出所有可用的GPU设备"""
        platforms = cl.get_platforms()
        print("\n可用的平台和设备：")
        for i, platform in enumerate(platforms):
            print(f"\n平台 {i}: {platform.name}")
            print(f"供应商: {platform.vendor}")
            print(f"版本: {platform.version}")
            
            devices = platform.get_devices(device_type=cl.device_type.ALL)
            for j, device in enumerate(devices):
                print(f"\n  设备 {j}:")
                print(f"    名称: {device.name}")
                print(f"    类型: {cl.device_type.to_string(device.type)}")
                print(f"    最大计算单元: {device.max_compute_units}")
                print(f"    全局内存: {device.global_mem_size / (1024*1024*1024):.2f} GB")
                print(f"    本地内存: {device.local_mem_size / 1024:.2f} KB")
                print(f"    最大工作组大小: {device.max_work_group_size}")

    def init_gpu(self, platform_index=None, device_index=None):
        """初始化最优的计算设备"""
        platforms = cl.get_platforms()
        
        if not platforms:
            print("未找到OpenCL平台，将使用CPU模式")
            return

        selected_device = None
        selected_platform = None

        # 首先寻找NVIDIA平台
        for platform in platforms:
            if 'nvidia' in platform.name.lower():
                devices = platform.get_devices(device_type=cl.device_type.GPU)
                if devices:
                    selected_device = devices[0]
                    selected_platform = platform
                    print("使用NVIDIA GPU:", selected_device.name)
                    break

        # 如果没有NVIDIA GPU，寻找Apple Silicon
        if not selected_device:
            for platform in platforms:
                if 'apple' in platform.name.lower():
                    devices = platform.get_devices(device_type=cl.device_type.GPU)
                    if devices:
                        selected_device = devices[0]
                        selected_platform = platform
                        print("使用Apple Silicon:", selected_device.name)
                        break

        # 如果既没有NVIDIA也没有Apple Silicon，使用第一个可用的GPU
        if not selected_device:
            for platform in platforms:
                devices = platform.get_devices(device_type=cl.device_type.GPU)
                if devices:
                    selected_device = devices[0]
                    selected_platform = platform
                    print("使用GPU:", selected_device.name)
                    break

        # 如果没有找到任何GPU，使用CPU
        if not selected_device:
            for platform in platforms:
                devices = platform.get_devices(device_type=cl.device_type.CPU)
                if devices:
                    selected_device = devices[0]
                    selected_platform = platform
                    print("未找到GPU，使用CPU:", selected_device.name)
                    break

        if selected_device:
            self.ctx = cl.Context([selected_device])
            self.queue = cl.CommandQueue(self.ctx)
            
            # 打印设备信息
            print(f"设备信息:")
            print(f"  计算单元: {selected_device.max_compute_units}")
            print(f"  全局内存: {selected_device.global_mem_size / (1024*1024*1024):.2f} GB")
        else:
            raise RuntimeError("未找到任何可用的计算设备")

    def _print_speed(self):
        """每秒输出一次生成速度和进度"""
        while self.running:
            time.sleep(1)  # 改为1秒
            current_time = time.time()
            current_count = self.total_generated
            
            time_diff = current_time - self.last_time
            count_diff = current_count - self.last_count
            
            if time_diff > 0:
                speed = count_diff / time_diff
                # 移除末尾的换行符，只使用\r
                print(f"\r当前速度: {speed:.2f} 个/秒 | "
                      f"已找到: {len(self.found_addresses)}/{self.target_count} | "
                      f"已尝试: {current_count} 个", end='', flush=True)
            
            self.last_time = current_time
            self.last_count = current_count

    def generate_mnemonic(self):
        """生成助记词"""
        m = mnemonic.Mnemonic('english')
        words = m.generate(strength=128)
        return words
    
    def generate_private_key(self):
        """生成随机私钥"""
        return secrets.token_hex(32)
    
    def create_wallet_from_mnemonic(self, mnemonic_words):
        """从助记词创建钱包"""
        seed = mnemonic.Mnemonic.to_seed(mnemonic_words)
        private_key = hashlib.sha256(seed).hexdigest()
        priv_key = PrivateKey(bytes.fromhex(private_key))
        addr = priv_key.public_key.to_base58check_address()
        return {
            'address': addr,
            'private_key': private_key,
            'mnemonic': mnemonic_words
        }
    
    def create_wallet_from_private_key(self, private_key):
        """从私钥创建钱包"""
        priv_key = PrivateKey(bytes.fromhex(private_key))
        addr = priv_key.public_key.to_base58check_address()
        return {
            'address': addr,
            'private_key': private_key,
            'mnemonic': ''  # 私钥模式下助记词为空字符串
        }
    
    def generate_wallet(self):
        """根据模式生成钱包"""
        if self.mode == 'mnemonic':
            mnemonic_words = self.generate_mnemonic()
            return self.create_wallet_from_mnemonic(mnemonic_words)
        else:
            private_key = self.generate_private_key()
            return self.create_wallet_from_private_key(private_key)
    
    def check_pattern(self, address, patterns):
        """检查地址是否符合模式（检查地址结尾，不区分大小写）"""
        # 将地址和所有模式都转换为小写进行比较
        address = address.lower()
        patterns = [pattern.strip().lower() for pattern in patterns]
        
        # 移除空字符串
        patterns = [p for p in patterns if p]
        
        if not patterns:
            return False
            
        for pattern in patterns:
            if address.endswith(pattern):
                return True
        return False
    
    def generate_addresses(self, patterns, count=1000):
        """生成指定数量的地址并检查是否符合模式"""
        # 保存目标数量
        self.target_count = count
        
        # 开始生成前初始化计数器和启动统计线程
        self.last_time = time.time()
        self.last_count = 0
        self.total_generated = 0
        self.running = True
        
        # 如果线程还没启动，则启动它
        if not self.speed_thread.is_alive():
            self.speed_thread.start()
        
        while len(self.found_addresses) < count and self.running:
            wallet = self.generate_wallet()
            self.total_generated += 1
            
            if self.check_pattern(wallet['address'], patterns):
                # 在输出新发现之前打印一个换行，以免覆盖速度显示
                print("\n")  # 额外的换行确保与速度显示分开
                print(f"靓号{len(self.found_addresses) + 1}地址: {wallet['address']}")
                if wallet['mnemonic']:  # 只有在有助记词时才显示
                    print(f"助记词: {wallet['mnemonic']}")
                print(f"私钥: {wallet['private_key']}")
                print("-" * 50)
                
                self.found_addresses.append(wallet)
                self.save_to_file(wallet)
    
    def save_to_file(self, wallet):
        """保存钱包信息到文件"""
        filename = 'found_addresses.json'
        
        # 添加生成时间和生成模式
        wallet['generate_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
        wallet['mode'] = self.mode
        
        try:
            with open(filename, 'a', encoding='utf-8') as f:
                json.dump(wallet, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"保存文件时出错: {str(e)}")
    
    def stop(self):
        """停止速度统计线程"""
        self.running = False
        if self.speed_thread.is_alive():
            self.speed_thread.join()

def main():
    # 选择生成模式
    while True:
        mode = input("\n请选择生成模式 (1: 助记词模式, 2: 私钥模式): ").strip()
        if mode in ('1', '2'):
            break
        print("输入无效，请重新选择")
    
    mode = 'mnemonic' if mode == '1' else 'privatekey'
    
    # 创建生成器实例（自动选择最优设备）
    generator = USDTAddressGenerator(mode=mode)
    
    # 设置靓号模式
    patterns = input("\n请输入想要的靓号模式（多个用逗号分隔，如：888,666,999）: ").split(',')
    count = int(input("请输入想要生成的靓号数量: "))
    
    print(f"\n开始生成靓号 (使用{('助记词' if mode == 'mnemonic' else '私钥')}模式)，请稍等...")
    start_time = time.time()
    
    try:
        generator.generate_addresses(patterns, count)
    except KeyboardInterrupt:
        print("\n程序已停止")
    finally:
        generator.stop()
    
    end_time = time.time()
    print(f"\n总共耗时: {end_time - start_time:.2f} 秒")
    print(f"总共尝试生成: {generator.total_generated} 个地址")
    print(f"生成的靓号地址已保存到 found_addresses.json 文件中")

if __name__ == "__main__":
    main()