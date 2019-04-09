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

-- --------------------------------------------------------

--
-- Structure for view `types`
--

CREATE ALGORITHM=UNDEFINED SQL SECURITY DEFINER VIEW `types`  AS  select `matches`.`type` AS `type`,count(0) AS `frequency`,avg(`matches`.`duration`) AS `duration`,avg(`matches`.`kills`) AS `kills`,avg(`matches`.`deaths`) AS `deaths`,avg(`matches`.`players`) AS `players`,if((avg(`matches`.`players`) = 0),NULL,(avg(`matches`.`kills`) / avg(`matches`.`players`))) AS `avg_kills`,if((avg(`matches`.`players`) = 0),NULL,(avg(`matches`.`deaths`) / avg(`matches`.`players`))) AS `avg_deaths` from `matches` where (`matches`.`duration` <> 0) group by `matches`.`type` order by `matches`.`type` ;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
