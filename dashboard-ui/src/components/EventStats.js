import React, { useEffect, useState } from 'react';
import '../App.css';

export default function EventStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null);

    const getEventStats = () => {
        fetch(`http://ec2-52-40-150-21.us-west-2.compute.amazonaws.com/event_logger/event_stats`) 
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
                <h1>Event Log Statistics</h1>
                {/* Directly access and display each event code's stats */}
                <div>0001 Events Logged: {stats.event_0001}</div>
                <div>0002 Events Logged: {stats.event_0002}</div>
                <div>0003 Events Logged: {stats.event_0003}</div>
                <div>0004 Events Logged: {stats.event_0004}</div>
            </div>
        );
    }
}
