<?php
/**
 * Database Connection Helper
 * 
 * Shared database connection configuration
 */

function getDatabaseConnection() {
    $dbPath = __DIR__ . '/projects/ai-team/team.db';
    
    // Also check Herd location
    if (!file_exists($dbPath)) {
        $dbPath = '/Users/ngs/Herd/ai-team-system/team.db';
    }
    
    if (!file_exists($dbPath)) {
        throw new Exception("Database not found at: $dbPath");
    }
    
    $dsn = "sqlite:$dbPath";
    $pdo = new PDO($dsn);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    
    return $pdo;
}
