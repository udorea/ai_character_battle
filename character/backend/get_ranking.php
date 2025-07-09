<?php
require_once 'db_config.php';
setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();
    $sql = "
        SELECT 
            id, 
            name, 
            wins, 
            losses, 
            (CASE 
                WHEN (wins + losses) > 0 THEN (wins / (wins + losses)) * 100 
                ELSE 0 
            END) AS win_rate_calc,
            (wins + losses) AS total_battles
        FROM characters
        ORDER BY 
            win_rate_calc DESC, 
            wins DESC, 
            name ASC;
    ";
    
    $result = $conn->query($sql);

    $ranking_data = [];
    $rank = 1;
    while ($row = $result->fetch_assoc()) {
        $row['rank'] = $rank++;
        $row['win_rate'] = number_format($row['win_rate_calc'], 2) . '%';
        unset($row['win_rate_calc']);
        $ranking_data[] = $row;
    }

    echo json_encode($ranking_data);

    $conn->close();

} catch (Exception $e) {
    error_log("SQL Error (get_ranking.php): " . $e->getMessage());
    echo json_encode(["success" => false, "message" => $e->getMessage()]);
}
?>
