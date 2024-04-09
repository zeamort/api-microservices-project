import React, { useEffect, useState } from 'react'
import '../App.css';

export default function AppStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null)

	const getStats = () => {
	
        fetch(`http://ec2-52-40-150-21.us-west-2.compute.amazonaws.com/processing/stats`)
            .then(res => res.json())
            .then((result)=>{
				console.log("Received Stats")
                setStats(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    }
    useEffect(() => {
		const interval = setInterval(() => getStats(), 2000); // Update every 2 seconds
		return() => clearInterval(interval);
    }, [getStats]);

    if (error){
        return (<div className={"error"}>Error found when fetching from API</div>)
    } else if (isLoaded === false){
        return(<div>Loading...</div>)
    } else if (isLoaded === true){
        return(
            <div>
                <h1>Latest Stats</h1>
                <table className={"StatsTable"}>
					<tbody>
						<tr>
							<th>Blood Pressure</th>
							<th>Heart Rate</th>
						</tr>
						<tr>
							<td># PU: {stats['total_power_usage_events']}</td>
							<td># LO: {stats['total_location_events']}</td>
						</tr>
						<tr>
							<td colspan="2">Max Power Usage: {stats['max_power_W']}</td>
						</tr>
						<tr>
							<td colspan="2">Max Temperature C: {stats['max_temperature_C']}</td>
						</tr>
						<tr>
							<td colspan="2">Average SoC %: {stats['average_state_of_charge']}</td>
						</tr>
					</tbody>
                </table>
                <h3>Last Updated: {stats['date_created']}</h3>

            </div>
        )
    }
}
