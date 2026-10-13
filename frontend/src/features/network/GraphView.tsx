import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Path, UserSummary } from "../../lib/types";
import { initials } from "../../lib/format";

export function GraphView({
  current,
  people = [],
  path,
}: {
  current: UserSummary;
  people?: UserSummary[];
  path?: Path;
}) {
  const graph = useMemo(() => {
    const members = path
      ? path.vertices
      : [current, ...people.filter((person) => person.id !== current.id)].slice(
          0,
          32,
        );
    const nodes: Node[] = members.map((person, index) => ({
      id: person.id,
      position: path
        ? { x: index * 245 + 20, y: 100 + (index % 2) * 35 }
        : index === 0
          ? { x: 350, y: 235 }
          : {
              x:
                350 +
                Math.cos(
                  ((index - 1) * Math.PI * 2) / Math.max(people.length, 1),
                ) *
                  285,
              y:
                235 +
                Math.sin(
                  ((index - 1) * Math.PI * 2) / Math.max(people.length, 1),
                ) *
                  195,
            },
      className: `person-node ${person.id === current.id ? "self-node" : path && index === members.length - 1 ? "target-node" : ""}`,
      data: {
        label: (
          <Link
            to={person.id === current.id ? "/profile" : `/people/${person.id}`}
            className="graph-person"
          >
            <span className="avatar">{initials(person.display_name)}</span>
            <strong>
              {person.id === current.id ? "Bạn" : person.display_name}
            </strong>
            <small>
              {path && index === members.length - 1
                ? "Người giới thiệu"
                : person.headline || "Kết nối nghề nghiệp"}
            </small>
          </Link>
        ),
      },
    }));
    const edges: Edge[] = path
      ? members.slice(1).map((person, index) => ({
          id: path.edges[index]?.id || `${members[index].id}-${person.id}`,
          source: members[index].id,
          target: person.id,
          type: "smoothstep",
          label: "Kết nối",
          style: { stroke: "#15786a", strokeWidth: 2 },
          labelStyle: { fill: "#4f625d", fontSize: 11 },
          labelBgStyle: { fill: "#f7faf8" },
        }))
      : members.slice(1).map((person) => ({
          id: `${current.id}-${person.id}`,
          source: current.id,
          target: person.id,
          type: "straight",
          style: { stroke: "#a9c6bd", strokeWidth: 1.5 },
        }));
    return { nodes, edges };
  }, [current, people, path]);
  return (
    <div
      className={`graph-canvas ${path ? "path-canvas" : ""}`}
      role="region"
      aria-label={
        path ? "Đồ thị đường giới thiệu đã chọn" : "Đồ thị kết nối trực tiếp"
      }
    >
      <ReactFlow
        key={path?.path_key || people.map((p) => p.id).join(",")}
        nodes={graph.nodes}
        edges={graph.edges}
        fitView
        fitViewOptions={{ padding: 0.28, maxZoom: 1.1 }}
        minZoom={0.25}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        ariaLabelConfig={{
          "controls.zoomIn.ariaLabel": "Phóng to",
          "controls.zoomOut.ariaLabel": "Thu nhỏ",
          "controls.fitView.ariaLabel": "Vừa khung nhìn",
        }}
      >
        <Background color="#cfddd6" gap={22} size={1.5} />
        <Controls showInteractive={false} />
      </ReactFlow>
      <div className="graph-legend">
        <span>
          <i className="legend-dot green" />
          Bạn
        </span>
        <span>
          <i className="legend-dot neutral" />
          Kết nối
        </span>
        {path && (
          <span>
            <i className="legend-dot gold" />
            Người giới thiệu
          </span>
        )}
      </div>
    </div>
  );
}
