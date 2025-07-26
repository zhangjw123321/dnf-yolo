"""
singletons.py - 全局单例管理器
确保ActionController和YaoqiAttacker在整个应用中只创建一次
"""

class GlobalSingletons:
    """全局单例管理器"""
    
    _action_controller = None
    _yaoqi_attacker = None
    _yolo_model = None
    _initialized = False
    _enabled = False  # 新增：控制是否允许创建实例
    
    @classmethod
    def get_action_controller(cls):
        """获取ActionController单例"""
        if not cls._enabled:
            print("⚠️  单例管理器未启用，无法创建ActionController实例")
            return None
        if cls._action_controller is None:
            print("⚡ 首次创建ActionController全局单例")
            from actions import ActionController
            
            # 确保YOLO模型先加载，让ActionController使用它
            if cls._yolo_model is None:
                print("📋 先加载全局YOLO模型...")
                cls.get_yolo_model()
            
            # ActionController使用共享的YOLO模型
            print("📋 ActionController使用全局共享YOLO模型")
            cls._action_controller = ActionController(yolo_model=cls._yolo_model)
            print("✅ ActionController全局单例创建完成")
        return cls._action_controller
    
    @classmethod
    def get_yaoqi_attacker(cls):
        """获取YaoqiAttacker单例"""
        if not cls._enabled:
            print("⚠️  单例管理器未启用，无法创建YaoqiAttacker实例")
            return None
        if cls._yaoqi_attacker is None:
            print("⚡ 首次创建YaoqiAttacker全局单例")
            from yaoqi_attack import YaoqiAttacker
            
            # 如果YOLO模型已经加载，共享它
            if cls._yolo_model is not None:
                print("📋 YaoqiAttacker使用已加载的全局YOLO模型")
                cls._yaoqi_attacker = YaoqiAttacker(yolo_model=cls._yolo_model)
            else:
                print("📋 YaoqiAttacker独立加载YOLO模型")
                cls._yaoqi_attacker = YaoqiAttacker()
            print("✅ YaoqiAttacker全局单例创建完成")
        return cls._yaoqi_attacker
    
    @classmethod
    def get_yolo_model(cls):
        """获取YOLO模型单例"""
        if not cls._enabled:
            print("⚠️  单例管理器未启用，无法创建YOLO模型实例")
            return None
        if cls._yolo_model is None:
            print("⚡ 首次加载YOLO模型全局单例")
            try:
                from ultralytics import YOLO
                cls._yolo_model = YOLO('models/best.pt')
                print("✅ YOLO模型全局单例加载完成")
            except Exception as e:
                print(f"❌ YOLO模型加载失败: {e}")
                cls._yolo_model = None
        return cls._yolo_model
    
    @classmethod
    def enable_singletons(cls):
        """启用单例管理器，允许创建实例"""
        cls._enabled = True
        print("🔓 单例管理器已启用")
    
    @classmethod
    def disable_singletons(cls):
        """禁用单例管理器，阻止创建新实例"""
        cls._enabled = False
        print("🔒 单例管理器已禁用")
    
    @classmethod
    def initialize_all(cls):
        """初始化所有单例（可选的预加载）"""
        if not cls._enabled:
            print("⚠️ 单例管理器未启用，无法初始化")
            return
        if not cls._initialized:
            print("🚀 初始化所有全局单例...")
            cls.get_action_controller()
            cls.get_yaoqi_attacker() 
            cls.get_yolo_model()
            cls._initialized = True
            print("✅ 所有全局单例初始化完成")
    
    @classmethod
    def reset_all(cls):
        """重置所有单例（测试用）"""
        print("🔄 重置所有全局单例")
        cls._action_controller = None
        cls._yaoqi_attacker = None
        cls._yolo_model = None
        cls._initialized = False


# 便捷的全局函数
def get_action_controller():
    """获取ActionController单例的便捷函数"""
    return GlobalSingletons.get_action_controller()

def get_yaoqi_attacker():
    """获取YaoqiAttacker单例的便捷函数"""
    return GlobalSingletons.get_yaoqi_attacker()

def get_yolo_model():
    """获取YOLO模型单例的便捷函数"""
    return GlobalSingletons.get_yolo_model()

def enable_singletons():
    """启用单例管理器的便捷函数"""
    return GlobalSingletons.enable_singletons()

def disable_singletons():
    """禁用单例管理器的便捷函数"""
    return GlobalSingletons.disable_singletons()

def initialize_singletons():
    """初始化所有单例的便捷函数"""
    return GlobalSingletons.initialize_all()