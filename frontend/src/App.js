import React, { useState, useEffect } from "react";
import { Container, Box, Typography, Grid, Paper } from "@mui/material";
import api from "./api";
import "./App.css";

function App() {
  const [anomalyData, setAnomalyData] = useState([]);
  const [scalingData, setScalingData] = useState({});
  const [remediationHistory, setRemediationHistory] = useState([]);
  const [llmResponses, setLlmResponses] = useState([]);

  useEffect(() => {
    // Fetch data initially and set up polling
    fetchData();
    const interval = setInterval(fetchData, 30000); // Poll every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const anomalies = await api.get("/api/anomalies");
      const scaling = await api.get("/api/scaling");
      const remediation = await api.get("/api/remediation");
      const llm = await api.get("/api/llm-responses");

      setAnomalyData(anomalies.data);
      setScalingData(scaling.data);
      setRemediationHistory(remediation.data);
      setLlmResponses(llm.data);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Self-Healing System Monitor
        </Typography>

        <Grid container spacing={3}>
          {/* Anomaly Detection Panel */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Anomaly Detection</Typography>
              {anomalyData.map((anomaly, index) => (
                <Box key={index} sx={{ mt: 1 }}>
                  <Typography>
                    Service: {anomaly.service}
                    <br />
                    Type: {anomaly.type}
                    <br />
                    Timestamp: {new Date(anomaly.timestamp).toLocaleString()}
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Grid>

          {/* Auto Scaling Panel */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Auto Scaling Status</Typography>
              {Object.entries(scalingData).map(([service, status]) => (
                <Box key={service} sx={{ mt: 1 }}>
                  <Typography>
                    {service}: {status.current_instances} instances (Min:{" "}
                    {status.min_instances}, Max: {status.max_instances})
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Grid>

          {/* Remediation History Panel */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Remediation History</Typography>
              {remediationHistory.map((item, index) => (
                <Box key={index} sx={{ mt: 1 }}>
                  <Typography>
                    Action: {item.action}
                    <br />
                    Status: {item.status}
                    <br />
                    Timestamp: {new Date(item.timestamp).toLocaleString()}
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Grid>

          {/* LLM Responses Panel */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">LLM Responses</Typography>
              {llmResponses.map((response, index) => (
                <Box key={index} sx={{ mt: 1 }}>
                  <Typography>
                    Query: {response.query}
                    <br />
                    Response: {response.response}
                    <br />
                    Timestamp: {new Date(response.timestamp).toLocaleString()}
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
}

export default App;
