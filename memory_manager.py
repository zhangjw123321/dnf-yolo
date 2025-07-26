"""
memory_manager.py - 内存管理工具
用于优化程序的内存使用和提高稳定性
"""

import gc
import psutil
import time
import threading
from typing import Optional


class MemoryManager:
    """内存管理器"""
    
    def __init__(self, max_memory_mb: int = 2048, check_interval: float = 30.0):
        """初始化内存管理器
        
        Args:
            max_memory_mb: 最大内存使用量（MB）
            check_interval: 检查间隔（秒）
        """
        self.max_memory_mb = max_memory_mb
        self.check_interval = check_interval
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.force_gc_threshold = max_memory_mb * 0.8  # 80%时强制垃圾回收
        
    def get_memory_usage(self) -> float:
        """获取当前进程内存使用量（MB）"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # 转换为MB
        except Exception:
            return 0.0
    
    def get_memory_percent(self) -> float:
        """获取内存使用百分比"""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0
    
    def force_garbage_collection(self):
        """强制垃圾回收 - 增强版"""
        try:
            total_collected = 0
            
            # 多次调用gc.collect()以确保彻底清理
            for i in range(5):  # 增加清理轮数
                collected = gc.collect()
                total_collected += collected
                if collected == 0:
                    break
                # 短暂等待让系统处理
                time.sleep(0.01)
            
            # 清理OpenCV缓存
            try:
                import cv2
                cv2.destroyAllWindows()
            except:
                pass
            
            # 清理numpy缓存
            try:
                import numpy as np
                # numpy没有直接的缓存清理方法，但我们可以触发gc
                pass
            except:
                pass
                
            # 清理YOLO相关缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
                
            print(f"🧹 增强内存清理完成，总回收对象数: {total_collected}")
            return True
        except Exception as e:
            print(f"❌ 内存清理失败: {e}")
            return False
    
    def check_memory_and_cleanup(self) -> bool:
        """检查内存使用并在必要时清理 - 更积极的策略"""
        current_memory = self.get_memory_usage()
        memory_percent = self.get_memory_percent()
        
        # 更积极的内存清理策略
        should_cleanup = False
        
        if current_memory > self.force_gc_threshold:
            print(f"⚠️ 进程内存使用过高: {current_memory:.1f}MB (阈值: {self.force_gc_threshold:.1f}MB)")
            should_cleanup = True
        elif memory_percent > 80:  # 降低系统内存阈值
            print(f"⚠️ 系统内存使用过高: {memory_percent:.1f}% (阈值: 80%)")
            should_cleanup = True
        elif current_memory > self.max_memory_mb * 0.5:  # 50%时也进行定期清理
            print(f"🔄 定期内存清理: {current_memory:.1f}MB ({memory_percent:.1f}%)")
            should_cleanup = True
            
        if should_cleanup:
            return self.force_garbage_collection()
        
        return False
    
    def start_monitoring(self):
        """开始内存监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("📊 内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        print("📊 内存监控已停止")
    
    def _monitor_loop(self):
        """内存监控循环"""
        while self.is_monitoring:
            try:
                current_memory = self.get_memory_usage()
                memory_percent = self.get_memory_percent()
                
                # 每次检查都尝试清理
                if current_memory > self.max_memory_mb * 0.6:  # 60%时开始关注
                    print(f"📊 内存使用: {current_memory:.1f}MB ({memory_percent:.1f}%)")
                    
                # 检查并清理
                self.check_memory_and_cleanup()
                
                # 动态调整检查间隔
                if current_memory > self.max_memory_mb * 0.7:
                    # 内存使用高时更频繁检查
                    time.sleep(min(self.check_interval, 15.0))
                else:
                    time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"内存监控错误: {e}")
                time.sleep(self.check_interval)
    
    def get_status(self) -> dict:
        """获取内存状态"""
        return {
            'current_memory_mb': self.get_memory_usage(),
            'memory_percent': self.get_memory_percent(),
            'max_memory_mb': self.max_memory_mb,
            'is_monitoring': self.is_monitoring
        }


# 全局内存管理器实例
memory_manager = MemoryManager(max_memory_mb=2048, check_interval=30.0)


def optimize_memory():
    """快速内存优化函数"""
    return memory_manager.force_garbage_collection()


def start_memory_monitoring():
    """启动内存监控"""
    memory_manager.start_monitoring()


def stop_memory_monitoring():
    """停止内存监控"""
    memory_manager.stop_monitoring()


def get_memory_status():
    """获取内存状态"""
    return memory_manager.get_status()


if __name__ == "__main__":
    # 测试内存管理器
    print("测试内存管理器...")
    
    # 启动监控
    start_memory_monitoring()
    
    # 显示当前状态
    status = get_memory_status()
    print(f"当前内存使用: {status['current_memory_mb']:.1f}MB ({status['memory_percent']:.1f}%)")
    
    # 测试内存清理
    optimize_memory()
    
    time.sleep(5)
    
    # 停止监控
    stop_memory_monitoring()
    
    print("测试完成")