import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Background,
  Controls,
  ReactFlow,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { CatalogJob } from "./types";

export function SkillGraph({
  root,
  jobs,
}: {
  root: CatalogJob;
  jobs: CatalogJob[];
}) {
  const graph = useMemo(() => {
    const skills = root.requirements.slice(0, 10);
    const related = jobs
      .filter(
        (j) =>
          j.id !== root.id &&
          j.requirements.some((s) => skills.some((k) => k.id === s.id)),
      )
      .slice(0, 5);
    const nodes: Node[] = [
      {
        id: `job:${root.id}`,
        position: { x: 0, y: 150 },
        className: "explore-node job-root",
        data: { label: root.title },
      },
    ];
    const edges: Edge[] = [];
    skills.forEach((skill, i) => {
      nodes.push({
        id: `skill:${skill.id}`,
        position: { x: 290, y: i * 90 },
        className: "explore-node skill-node",
        data: { label: skill.name },
      });
      edges.push({
        id: `root:${skill.id}`,
        source: `job:${root.id}`,
        target: `skill:${skill.id}`,
        label: "Yêu cầu kỹ năng",
        type: "smoothstep",
      });
    });
    nodes.push({
      id: "location",
      position: { x: 0, y: 330 },
      className: "explore-node location-node",
      data: { label: `Địa điểm: ${root.location}` },
    });
    edges.push({
      id: "at-location",
      source: `job:${root.id}`,
      target: "location",
      type: "smoothstep",
    });
    related.forEach((job, i) => {
      nodes.push({
        id: `job:${job.id}`,
        position: { x: 580, y: i * 130 + 30 },
        className: "explore-node",
        data: {
          label: <Link to={`/explore/jobs/${job.id}`}>{job.title}</Link>,
        },
      });
      job.requirements.forEach((s) => {
        if (skills.some((k) => k.id === s.id))
          edges.push({
            id: `${job.id}:${s.id}`,
            source: `job:${job.id}`,
            target: `skill:${s.id}`,
            type: "smoothstep",
          });
      });
    });
    return {
      nodes,
      edges,
      related,
      truncated:
        root.requirements.length > skills.length ||
        jobs.filter(
          (j) =>
            j.id !== root.id &&
            j.requirements.some((s) => skills.some((k) => k.id === s.id)),
        ).length > related.length,
    };
  }, [root, jobs]);
  return (
    <>
      <div
        className="explore-graph"
        aria-label="Đồ thị quan hệ việc làm và kỹ năng"
      >
        <ReactFlow
          key={root.id}
          defaultNodes={graph.nodes}
          defaultEdges={graph.edges}
          fitView
          nodesDraggable
          nodesConnectable={false}
          minZoom={0.3}
          maxZoom={1.5}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="tag-row graph-key">
        <span>
          <i className="key-job" />
          Việc làm
        </span>
        <span>
          <i className="key-skill" />
          Kỹ năng
        </span>
        <span>
          <i className="key-location" />
          Địa điểm
        </span>
      </div>
      <p className="muted">
        Quan hệ từ yêu cầu kỹ năng trong catalog; chưa phải graph VietJobs sau
        Spark.{" "}
        {graph.truncated
          ? "Đã giới hạn 10 kỹ năng và 5 việc liên quan."
          : "Hiển thị các việc liên quan có kỹ năng chung."}
      </p>
      <div className="tag-row" aria-label="Các việc liên quan trong đồ thị">
        {graph.related.map((j) => (
          <Link key={j.id} className="text-link" to={`/explore/jobs/${j.id}`}>
            {j.title} →
          </Link>
        ))}
      </div>
    </>
  );
}
