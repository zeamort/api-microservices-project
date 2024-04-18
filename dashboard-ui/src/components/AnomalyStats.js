import React, { useEffect, useState } from 'react';
import '../App.css';

export default function AnomalyStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null);

    const getEventStats = () => {
        fetch(`http://ec2-52-40-150-21.us-west-2.compute.amazonaws.com/anomaly_detector/anomaly_stats`) 
            .then(res => res.json())
            .then(
                (result) => {
                    console.log("Received Event Stats", result);
                    setStats(result);
                    setIsLoaded(true);
                },
                (error) => {
                    setError(error);
                    setIsLoaded(true);
                }
            );
    };

    useEffect(() => {
        const interval = setInterval(getEventStats, 2000); // Update every 2 seconds
        return () => clearInterval(interval);
    }, []);

    if (error) {
        return <div className="error">Error: {error.message}</div>;
    } else if (!isLoaded) {
        return <div>Loading...</div>;
    } else {
        return (
            <div>
                <h1>Anomaly Statistics</h1>
                {/* Directly access and display each event code's stats */}
                <div>High Temp Anomalies: {stats['num_anomalies']['High Temp']}</div>
                <div>Low SoC Anomalies: {stats['num_anomalies']['Low SoC']}</div>
                <div>{stats['most_recent_desc']}</div>
                <div>{stats['most_recent_datetime']}</div>
            </div>
        );
    }
}
