/**
 * Progressive enhancement for graph visualization using D3.js
 */

function initializeD3Graph(graphData) {
    // Only enhance if we have data and D3 is loaded
    if (!graphData || !window.d3) return;
    
    const svg = d3.select("#graph-svg");
    const width = 1000;
    const height = 800;
    
    // Clear existing static content and prepare for D3
    svg.selectAll(".nodes, .edges").remove();
    
    // Create groups for edges and nodes
    const g = svg.append("g").attr("class", "graph-content");
    const edgesGroup = g.append("g").attr("class", "edges");
    const nodesGroup = g.append("g").attr("class", "nodes");
    
    // Set up zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            g.attr("transform", event.transform);
        });
    
    svg.call(zoom);
    
    // Create force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.edges)
            .id(d => d.id)
            .distance(100))
        .force("charge", d3.forceManyBody()
            .strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide()
            .radius(d => d.radius || 10));
    
    // Create edges
    const edges = edgesGroup.selectAll("line")
        .data(graphData.edges)
        .enter().append("line")
        .attr("class", "graph-edge")
        .attr("stroke", "#888")
        .attr("stroke-width", 1)
        .attr("opacity", 0.5)
        .attr("marker-end", "url(#arrowhead)");
    
    // Create node groups
    const nodes = nodesGroup.selectAll("g")
        .data(graphData.nodes)
        .enter().append("g")
        .attr("class", "graph-node")
        .attr("data-id", d => d.id)
        .attr("data-type", d => d.type)
        .call(drag(simulation));
    
    // Add shapes based on node type
    nodes.each(function(d) {
        const node = d3.select(this);
        
        if (d.type === "country") {
            node.append("rect")
                .attr("x", -15)
                .attr("y", -15)
                .attr("width", 30)
                .attr("height", 30)
                .attr("fill", "#FF6B6B")
                .attr("opacity", 0.8)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
        } else {
            const color = d.type === "band" ? "#FFD700" : 
                         d.type === "person" ? "#4B9BFF" : "#888";
            const radius = d.radius || (d.type === "band" ? 10 : 8);
            
            node.append("circle")
                .attr("r", radius)
                .attr("fill", color)
                .attr("opacity", 0.8)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
        }
        
        // Add labels
        node.append("text")
            .attr("y", (d.radius || 10) + 15)
            .attr("text-anchor", "middle")
            .attr("font-size", "10px")
            .attr("fill", "#fff")
            .attr("opacity", 0.8)
            .style("pointer-events", "none")
            .text(d => d.name.length > 20 ? d.name.substring(0, 20) + "..." : d.name);
    });
    
    // Add hover effects
    nodes.on("mouseover", function(event, d) {
        d3.select(this).select("circle, rect")
            .transition()
            .duration(200)
            .attr("opacity", 1)
            .attr("stroke-width", 2);
        
        // Highlight connected edges
        edges.attr("opacity", e => 
            e.source.id === d.id || e.target.id === d.id ? 1 : 0.2
        );
    })
    .on("mouseout", function(event, d) {
        d3.select(this).select("circle, rect")
            .transition()
            .duration(200)
            .attr("opacity", 0.8)
            .attr("stroke-width", 1);
        
        edges.attr("opacity", 0.5);
    });
    
    // Add click navigation
    nodes.on("click", function(event, d) {
        if (d.type === "band") {
            window.location.href = `/bands/${d.id}`;
        } else if (d.type === "person" && d.id.startsWith("person_")) {
            window.location.href = `/people/${d.id.replace("person_", "")}`;
        }
    });
    
    // Add tooltips
    const tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("position", "absolute")
        .style("padding", "10px")
        .style("background", "rgba(0, 0, 0, 0.9)")
        .style("color", "#fff")
        .style("border-radius", "5px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("opacity", 0);
    
    nodes.on("mouseover", function(event, d) {
        let content = `<strong>${d.name}</strong><br/>`;
        content += `Type: ${d.type}<br/>`;
        if (d.year) content += `Year: ${d.year}<br/>`;
        if (d.country) content += `Country: ${d.country}<br/>`;
        if (d.connections) content += `Connections: ${d.connections}<br/>`;
        if (d.band_count) content += `Bands: ${d.band_count}<br/>`;
        
        tooltip.html(content)
            .style("opacity", 1)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
    .on("mousemove", function(event) {
        tooltip.style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
    .on("mouseout", function() {
        tooltip.style("opacity", 0);
    });
    
    // Update positions on simulation tick
    simulation.on("tick", () => {
        edges
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        
        nodes.attr("transform", d => `translate(${d.x}, ${d.y})`);
    });
    
    // Drag behavior
    function drag(simulation) {
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }
    
    // Controls
    d3.select("body").on("keydown", function(event) {
        switch(event.key) {
            case "+":
            case "=":
                zoom.scaleBy(svg.transition().duration(750), 1.2);
                break;
            case "-":
            case "_":
                zoom.scaleBy(svg.transition().duration(750), 0.8);
                break;
            case "0":
                svg.transition().duration(750).call(
                    zoom.transform,
                    d3.zoomIdentity
                );
                break;
        }
    });
}

// Make function available globally
window.initializeD3Graph = initializeD3Graph;