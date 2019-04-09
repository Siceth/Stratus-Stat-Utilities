SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `stratus`
--
CREATE DATABASE IF NOT EXISTS `stratus` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `stratus`;

-- --------------------------------------------------------

--
-- Table structure for table `growth`
--

CREATE TABLE `growth` (
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `players` int(11) UNSIGNED NOT NULL,
  `matches` int(11) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `matches`
--

CREATE TABLE `matches` (
  `uid` varchar(36) NOT NULL,
  `start_timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `end_timestamp` timestamp NULL DEFAULT NULL,
  `map` varchar(255) NOT NULL,
  `type` varchar(10) NOT NULL,
  `duration` mediumint(8) UNSIGNED NOT NULL,
  `kills` smallint(5) UNSIGNED NOT NULL,
  `deaths` smallint(5) UNSIGNED NOT NULL,
  `players` smallint(5) UNSIGNED NOT NULL,
  `winner` varchar(255) DEFAULT NULL,
  `prev_uuid` varchar(36) DEFAULT NULL,
  `next_uuid` varchar(36) DEFAULT NULL,
  `cached` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `players`
--

CREATE TABLE `players` (
  `uuid` varchar(36) NOT NULL,
  `username` varchar(16) NOT NULL,
  `kills` int(11) NOT NULL,
  `deaths` int(11) NOT NULL,
  `friends` int(11) NOT NULL,
  `kill_rank` int(11) NOT NULL,
  `droplets` int(11) NOT NULL,
  `monuments` mediumint(8) UNSIGNED NOT NULL,
  `wools` mediumint(8) UNSIGNED NOT NULL,
  `cores` mediumint(8) UNSIGNED NOT NULL,
  `flags` mediumint(8) UNSIGNED NOT NULL,
  `ranks` tinyint(3) UNSIGNED NOT NULL,
  `staff` tinyint(1) NOT NULL,
  `donor` tinyint(1) NOT NULL,
  `tournament_winner` tinyint(1) NOT NULL,
  `first_joined` date NOT NULL,
  `hours_played` mediumint(8) UNSIGNED NOT NULL,
  `teams_joined` mediumint(8) UNSIGNED NOT NULL,
  `trophies` tinyint(3) UNSIGNED NOT NULL,
  `has_team` tinyint(1) NOT NULL,
  `kd` float(7,3) UNSIGNED NOT NULL,
  `average_kills_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_deaths_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_monuments_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_wools_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_cores_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_flags_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_droplets_per_hour` float(10,3) UNSIGNED NOT NULL,
  `average_new_friends_per_hour` float(7,3) UNSIGNED NOT NULL,
  `average_experienced_game_length_in_minutes` float(6,3) UNSIGNED NOT NULL,
  `average_kills_per_game` float(5,3) UNSIGNED NOT NULL,
  `khpdg` float(7,5) UNSIGNED NOT NULL,
  `percent_time_spent_on_stratus` float(6,2) UNSIGNED NOT NULL,
  `percent_waking_time_spent_on_stratus` float(6,2) UNSIGNED NOT NULL,
  `kill_based_merit` float(5,4) UNSIGNED NOT NULL,
  `time_based_merit` float(5,4) UNSIGNED NOT NULL,
  `merit_multiplier` float(5,4) UNSIGNED NOT NULL,
  `reliability_index` float(5,4) UNSIGNED NOT NULL,
  `hours_until_one_million_droplets` mediumint(8) UNSIGNED NOT NULL,
  `cached` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Stand-in structure for view `types`
-- (See below for the actual view)
--
CREATE TABLE `types` (
`type` varchar(10)
,`frequency` bigint(21)
,`duration` decimal(12,4)
,`kills` decimal(9,4)
,`deaths` decimal(9,4)
,`players` decimal(9,4)
,`avg_kills` decimal(17,8)
,`avg_deaths` decimal(17,8)
);

-- --------------------------------------------------------

--
-- Structure for view `types`
--
DROP TABLE IF EXISTS `types`;

CREATE ALGORITHM=UNDEFINED SQL SECURITY DEFINER VIEW `types`  AS  select `matches`.`type` AS `type`,count(0) AS `frequency`,avg(`matches`.`duration`) AS `duration`,avg(`matches`.`kills`) AS `kills`,avg(`matches`.`deaths`) AS `deaths`,avg(`matches`.`players`) AS `players`,if((avg(`matches`.`players`) = 0),NULL,(avg(`matches`.`kills`) / avg(`matches`.`players`))) AS `avg_kills`,if((avg(`matches`.`players`) = 0),NULL,(avg(`matches`.`deaths`) / avg(`matches`.`players`))) AS `avg_deaths` from `matches` where (`matches`.`duration` <> 0) group by `matches`.`type` order by `matches`.`type` ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `growth`
--
ALTER TABLE `growth`
  ADD PRIMARY KEY (`timestamp`);

--
-- Indexes for table `matches`
--
ALTER TABLE `matches`
  ADD PRIMARY KEY (`uid`),
  ADD UNIQUE KEY `start_timestamp` (`start_timestamp`);

--
-- Indexes for table `players`
--
ALTER TABLE `players`
  ADD PRIMARY KEY (`uuid`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
