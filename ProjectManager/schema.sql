-- schema.sql
-- mysql中可以通过命令:mysql -u root -p < schema.sql来执行

drop database if exists awesome;

create database awesome;

use awesome;

grant select, insert, update, delete on awesome.* to 'www-data'@'localhost' identified by 'www-data';

CREATE TABLE `user` (
  `user_id` varchar(6) NOT NULL,
  `passwd` varchar(50) DEFAULT NULL,
  `user_name` varchar(10) DEFAULT NULL,
  `created_at` double DEFAULT NULL,
  `admin` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8；

CREATE TABLE `project` (
  `project_id` varchar(14) NOT NULL,
  `project_name` varchar(100) DEFAULT NULL,
  `project_level` varchar(1) DEFAULT NULL,
  `project_status` varchar(1) DEFAULT NULL,
  `project_stage` varchar(1) DEFAULT NULL,
  `project_docFlag` varchar(1) DEFAULT NULL,
  `created_at` double DEFAULT NULL,
  `project_manager` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8；

INSERT INTO `user` (`user_id`,`passwd`,`user_name`,`created_at`,`admin`) VALUES ('012419','f0f2cd64d983279779f6455e39c8682a4e6037d5','李欣',1518492331.27333,NULL);
INSERT INTO `user` (`user_id`,`passwd`,`user_name`,`created_at`,`admin`) VALUES ('012547','fd128238bb9afe4c4ad9bfa3db7a8c53f728da59','王峥',1518492282.24244,NULL);
INSERT INTO `user` (`user_id`,`passwd`,`user_name`,`created_at`,`admin`) VALUES ('016878','a9f1bfe5e179198b5856d81f4c951367da41974d','赵凯',1518145172.20085,'1');
INSERT INTO `user` (`user_id`,`passwd`,`user_name`,`created_at`,`admin`) VALUES ('018769','899e7cbf9769fed253797dd84d9301860ab6e509','栾博',1518492306.65649,NULL);

INSERT INTO `project` (`project_id`,`project_name`,`project_level`,`project_status`,`project_stage`,`project_docFlag`,`created_at`,`project_manager`) VALUES ('P2017112816202','银企对账系统功能升级（日终批处理及对账数据生成）','B','1','2','2',1518425492.78158,'赵凯');
INSERT INTO `project` (`project_id`,`project_name`,`project_level`,`project_status`,`project_stage`,`project_docFlag`,`created_at`,`project_manager`) VALUES ('P2017122516205','银企对账系统功能提升（财政授权零余额账户）','C','2','1','2',1518425398.99421,'赵凯');
INSERT INTO `project` (`project_id`,`project_name`,`project_level`,`project_status`,`project_stage`,`project_docFlag`,`created_at`,`project_manager`) VALUES ('P2017122616287','银企对账系统（新增分行以及调整分行层级）','C','1','1','1',1518425357.32454,'赵凯');
