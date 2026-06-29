# Value Model

This project is valuable only if it helps the department make better delivery decisions. The purpose is not to automate a table write; the purpose is to create a reliable current-quarter management signal.

## Management Questions

The Base output is designed to answer:

1. Is the current quarter's delivery load accumulating normally?
2. Are large or complex demands becoming a larger share of work?
3. Is the P90 delivery effort moving upward, indicating long-tail risk?
4. Is development effort increasing faster than testing effort?
5. Is the quarter being driven by demand count growth or by demand complexity?
6. Which category should be discussed in the next delivery review?

## Signals Produced

| Signal | Interpretation |
|---|---|
| Demand count | Throughput and workload accumulation |
| Average delivery effort | Overall delivery scale |
| Median delivery effort | Typical demand scale |
| P90 delivery effort | Long-tail complexity and risk |
| Average development effort | R&D resource pressure |
| Average testing effort | QA pressure and validation cost |
| Development/testing ratio | Effort structure and delivery balance |

## Review Usage

In a delivery review, the table can be used in this order:

1. Look at current-quarter cumulative demand count.
2. Compare `中小需求` and `大/超大需求`.
3. Check whether P90 is rising.
4. Check whether development and testing effort move together.
5. Identify whether the quarter is being driven by more demands or larger demands.
6. Record action items for demand splitting, resource balancing, or early risk review.

## Why Base Is The Right Archive

Feishu Base provides:

- stable shared access
- views and filters for review meetings
- simple charting
- formula fields such as `研发时长/测试时长`
- a stable latest snapshot without creating new weekly documents

The repository keeps calculation outside Base while using Base as the durable collaboration layer.

## What Should Be Added Later

Potential future enhancements:

- automated review commentary generation
- anomaly detection for sudden P90 jumps
- category-level trend visualization
- owner/team dimensions
- project-level drill-down
- automatic Feishu document summary linked to the Base table
