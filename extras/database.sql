SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

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

--
-- Indexes for dumped tables
--

--
-- Indexes for table `players`
--
ALTER TABLE `players`
  ADD PRIMARY KEY (`uuid`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
