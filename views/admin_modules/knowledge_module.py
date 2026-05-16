from views.user_modules.knowledge_module import KnowledgeBaseModule


class AdminKnowledgeModule(KnowledgeBaseModule):
    """管理员知识库模块，复用用户模块的完整功能，拥有全部删除权限"""
    def __init__(self, user, parent=None):
        super().__init__(user, is_admin=True, parent=parent)
