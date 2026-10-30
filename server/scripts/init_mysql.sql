-- 在 Navicat 里连接到本机 MySQL 后，新建查询并执行本文件。
-- 只负责建库；表结构由后端启动时自动创建（SQLAlchemy Base.metadata.create_all）。

CREATE DATABASE IF NOT EXISTS ai_chat
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
