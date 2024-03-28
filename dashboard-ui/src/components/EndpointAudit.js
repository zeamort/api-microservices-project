import React, { useEffect, useState } from 'react';
import '../App.css';

export default function EndpointAudit(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null);
    const [index, setIndex] = useState(null); // Added state for index

    const getAudit = () => {
        const rand_val = Math.floor(Math.random() * 100); // Moved inside getAudit to ensure freshness on each call
        fetch(`http://ec2-52-40-150-21.us-west-2.compute.amazonaws.com:8110/${props.endpoint}?index=${rand_val}`)
            .then(res => res.json())
            .then((result) => {
                console.log("Received Audit Results for " + props.endpoint);
                setLog(result);
                setIsLoaded(true);
                setIndex(rand_val); // Set index here to ensure synchronization
            }, (error) => {
                setError(error);
                setIsLoaded(true);
            });
    };

    useEffect(() => {
        const interval = setInterval(() => getAudit(), 4000); // Update every 4 seconds
        return () => clearInterval(interval);
    }, []); // Removed getAudit from dependency array to avoid re-creating interval on every render

    if (error) {
        return (<div className={"error"}>Error found when fetching from API</div>);
    } else if (!isLoaded) {
        return (<div>Loading...</div>);
    } else {
        // Use the state for index in the view
        return (
            <div>
                <h3>{`${props.endpoint}-${index}`}</h3>
                {JSON.stringify(log)}
            </div>
        );
    }
}
