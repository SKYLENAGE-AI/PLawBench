import re
import json_repair
import json

SYS_PROMPT = {
"legal_qa":"""
## 角色
你是一名评估员，你的任务是对照一份标有得分项的标准答案，在律师对当事人提问收集信息的过程中，对律师的表现进行打分，以评估律师在面对当事人时的理解和业务能力。

## 输入和输出格式
输入包含两部分：
1、待评分律师的提问问题清单（10-25条，已进行编号）
2、标准答案的rubric（总分N分；每个要点为“（+X分）要点描述”）
3、案情描述

输出格式固定为：
总分为「得分」/「总分」，得分率为「百分比」%
分析如下：
-要点1:「得分情况」，理由为：.......。
-要点2:「得分情况」，理由为：......。
-......
```json
    {
        "total_points": 模型得分,
        "max_points": 该题总分,
    },
```

## 评分规则
1、你无须对答案本身的准确性进行判断，只需严格按照标准答案，判断律师追问的问题中有没有相同或本质相同的内容，并计算最终得分。
2、只对前 <<num>> 条问题进行评价，多余部分的问题一律不考虑。
3、不得补充新问题、提供法律建议、评价当事人、复述长篇背景；只做对照与打分说明。
4、对标准rubric中的每个“问题点”，在待评分问题清单中寻找最佳匹配，按照匹配程度给分，如果完全覆盖关键要素，语义一致，给出100%的分数；如果命中核心主题，但缺少关键限定，例如标准要“报警记录及住院病历、诊断证明”，只问“有无报警”而未问病历，可以酌情给分；如果未覆盖语义关键点，则不给分。

""",
"document_generation":"""
## 角色和任务
你是一名评估员，你的任务是对照一份标有得分项的标准答案，对法律文书的写作情况进行打分。

## 输入和输出格式
输入包含两部分：
1、待评分的法律文书。
2、标准rubric

输出格式固定为：
总分为「得分」/「总分」，得分率为「百分比」%
分析如下：
-要点1:「得分情况」，理由为：.......。
-要点2:「得分情况」，理由为：......。
-......
```json
    {
        "total_points": 模型得分,
        "max_points": 该题总分,
    },
```

## 评分规则
1、你无须对答案本身的准确性进行判断，只需严格按照标准答案，判断模型的回答中有没有相同或本质相同的内容，并计算最终得分。
2、不得更改答案、提供法律建议、评价当事人、复述长篇背景；只做对照与打分说明。
3、对标准rubric中的每个“问题点”，在待评分问题清单中寻找最佳匹配，按照匹配程度给分，如果完全覆盖关键要素，语义一致，给出100%的分数；如果命中核心主题，但缺少关键限定，例如标准要“报警记录及住院病历、诊断证明”，只问“有无报警”而未问病历，可以酌情给分；如果未覆盖语义关键点，则不给分。
""",
"case_analysis_merge":"""
## 角色设定

你是一名严谨的法律实务评分专家，擅长根据精确的评分标准对法律实务问题的回答进行逐项检查。你严格遵守"提及即得分，未提及则扣分"的原则，不做主观推断。

## 核心任务

根据提供的详细评分细则（rubric），对法律实务题回答进行精确评分。回答分为四个部分：结论、法条依据、案件事实总结、推理过程。每个部分可能有独立的评分细则。

## 输入信息结构

**问题内容**：简要的案件描述和提问问题。

**评分细则（rubric）**：分为多个部分，每个部分的格式可能类似示例：       

结论评分细则

法条依据评分细则

案件事实评分细则

推理过程评分细则

其他部分评分细则

**待评分回答**：需要评分的文本，其中明确标有“结论”、“法条依据”、“案件事实”和“推理过程”四个部分。
    

## 评分原则

1.  **严格字面匹配**：以rubric中的表述为准，检查回答中是否有相同或实质相同的表述。
    
2.  **独立评分**：每个得分项独立计算，不考虑其他项。
    
3.  **不推断不补充**：仅根据回答中明确提及的内容评分，不进行推理或补充。
    
4.  **明确加分项扣分项**：严格按照分数进行加分和扣分操作。
    
5.  **酌情扣分**：在回答结果没有完全覆盖得分点时，根据已经答出的要点酌情给部分结果分。
    

## 评分流程

### 步骤1：分割回答

将回答分割为四个部分：

*   结论
    
*   法条依据即大前提
    
*   案件事实即小前提
    
*   推理过程
    

### 步骤2：分别评分

对每个部分，使用对应的rubric进行评分。每个部分的评分步骤：

1.  **解析rubric**：将rubric分解为得分项和扣分规则。
    
2.  **内容检查**：检查该部分回答中是否提及rubric要求的每个内容。
    

### 步骤3：整体结构评分（如果有）

如果rubric中包含对整体结构的评分，则根据整体结构的要求进行评分。

### 步骤4：汇总与反馈

## 输出格式

要求输出以下四个部分的详细评分，以及总分和整体反馈。

```json
{
  "score_details": {
    "法条依据": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [
        {
          "rubric_item": "具体得分项描述",
          "max_points": ...,
          "points_awarded": ...,
          "mentions": [...],
          "rationale": "评分理由"
        }
      ]
    },
    "案件事实": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    },
    "推理过程": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    },
    "结论": {
      "total_points": 0,
      "max_points": 0,
      "breakdown": [...]
    }     "others": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    }
  },
  "total_score": {
    "total_awarded": ...,
    "total_max": ...,
    "percentage": ...
  },
  "overall_feedback": {

    "strengths": [ ],


    "weaknesses": [ ],


    "suggestions": [ ]

  }
}

```""",
}


JUDGE_PROMPT = {
"legal_qa":"""
# 问答内容
<<conversation>>

# 评分细则
<<rubric_item>>

# 该题总分
<<score>>

# 输出格式
请按照指令，先分析，再给出得分，务必在回答的结尾按照以下json格式输出：
```json
    {
        "total_points": 模型得分,
        "max_points": 该题总分,
    },
```

""",
"document_generation":"""
# 问答内容
<<conversation>>

# 评分细则
<<rubric_item>>

# 该题总分
<<score>>

# 输出格式
请按照指令，先分析，再给出得分，务必在回答的结尾按照以下json格式输出：
```json
    {
        "total_points": 模型得分,
        "max_points": 该题总分,
    },
```

""",
"case_analysis_merge":"""
# 问题内容
<<conversation>>

# 评分细则
<<rubric_item>>

# 输出格式
请务必在回答的结尾按照以下json格式输出：

```json
{
  "score_details": {
    "法条依据": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [
        {
          "rubric_item": "具体得分项描述",
          "max_points": ...,
          "points_awarded": ...,
          "mentions": [...],
          "rationale": "评分理由"
        }
      ]
    },
    "案件事实": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    },
    "推理过程": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    },
    "结论": {
      "total_points": 0,
      "max_points": 0,
      "breakdown": [...]
    }     "others": {
      "total_points": ...,
      "max_points": ...,
      "breakdown": [...]
    }
  },
  "total_score": {
    "total_awarded": ...,
    "total_max": ...,
    "percentage": ...
  },
  "overall_feedback": {

    "strengths": [ ],


    "weaknesses": [ ],


    "suggestions": [ ]

  }
}

```
"""
}


# ==========================================
# 2. Helper Functions
# ==========================================


def parse_json_to_dict(json_string: str) -> dict:
    """
    Extracts and parses a JSON object from a string.
    """
    
    try:
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',      # ``` {...} ```
            r'(\{[^\{\}]*(?:\{[^\{\}]*\}[^\{\}]*)*\})',  # {...}
        ]
        
        json_str = None
        for pattern in patterns:
            match = re.search(pattern, json_string, re.DOTALL)
            if match:
                json_str = match.group(1)
                break
        
        if json_str is None:
            json_str = json_string.strip()
        
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        try:
            res = json.loads(json_str)
        except json.JSONDecodeError:
            res = json_repair.loads(json_str)
        
        if res is None:
            return {}
        if isinstance(res, list):
            return res[0] if res else {}
        if isinstance(res, dict):
            return res
        return {}
            
    except Exception as e:
        print(f"JSON Parsing failed: {type(e).__name__}: {e}")
        print(f"string: {json_string[:300]}...")
        return {}


def call_llm_api(messages: list) -> str:
    """
    Placeholder for the user's LLM API call.
    Replace this with actual API logic.
    """
    # Example:
    # response = openai.chat.completions.create(model="gpt-4", messages=messages)
    # return response.choices[0].message.content


# ==========================================
# 3. Main Evaluation Class
# ==========================================

class LegalEvaluator:
    """
    Unified evaluator for different legal tasks:
    - legal_qa (Legal QA Interview)
    - document_generation (Legal Writing)
    - case_analysis_merge (Complex Case Analysis)
    """

    def evaluate(self, item: dict, task_type: str) -> dict:
        """
        Main entry point to evaluate a single item.
        
        Args:
            item (dict): input data containing prompt, generated response, rubrics, etc.
            task_type (str): 'legal_qa', 'document_generation', or 'case_analysis_merge'
        
        Returns:
            dict: The item updated with score metrics.
        """
        if task_type not in SYS_PROMPT:
            raise ValueError(f"Unknown task_type: {task_type}")

        # 1. Prepare inputs
        gen_text = item.get('response', '')  # Model's output
        prompt_text = item.get('prompt', '') # Original User Prompt
        
        # Construct conversation string for the Judge
        convo_str = f"user: {prompt_text}\n\nassistant: {gen_text}\n\n"
        
        # 2. Build Prompt based on task type
        messages = self._build_messages(task_type, item, convo_str)
        
        # 3. Call Judge LLM
        llm_output = call_llm_api(messages)
        grading_response = parse_json_to_dict(llm_output)
        
        # 4. Calculate Scores based on task logic
        result = self._calculate_metrics(task_type, grading_response)
        
        # 5. Return combined result
        return {
            "task_type": task_type,
            "metrics": result,
            "raw_judge_output": grading_response
        }

    def evaluate_with_retry(self, item: dict, task_type: str, max_retries: int = 3) -> dict:
        """
        Wrapper method to handle LLM instability or JSON parsing errors.
        Users can use this to automatically retry when 'failed' is 1.
        """
        for attempt in range(max_retries):
            result = self.evaluate(item, task_type)
            
            # If failed is 0, it means success -> return immediately
            if result["metrics"].get("failed", 0) == 0:
                return result
            
            print(f"Attempt {attempt + 1} failed (JSON parse error or invalid score). Retrying...")
            # time.sleep(1)
        
        print(f"All {max_retries} attempts failed. Returning zero score.")
        return result
    
    def _build_messages(self, task_type: str, item: dict, convo_str: str) -> list:
        """Constructs the system and user messages for the LLM."""
        
        sys_template = SYS_PROMPT[task_type]
        user_template = JUDGE_PROMPT[task_type]
        
        # Standardize rubric input (some tasks might use different keys)
        rubrics_data = item.get("rubrics") or item.get("rubric") or item.get("Rubrics") or {}
        rubrics_str = json.dumps(rubrics_data, ensure_ascii=False, indent=2)

        # -- Task Specific Prompt logic --
        if task_type == "legal_qa":
            # Logic for max_num in Q&A task
            max_num = "25" if "mid" in item.get("task_name", "") else "50"
            sys_content = sys_template.replace("<<num>>", max_num)
            
            user_content = user_template \
                .replace("<<conversation>>", convo_str) \
                .replace("<<rubric_item>>", rubrics_str) \
                .replace("<<score>>", str(item["score"]))
                
        elif task_type == "document_generation":
            sys_content = sys_template
            user_content = user_template \
                .replace("<<conversation>>", convo_str) \
                .replace("<<rubric_item>>", rubrics_str) \
                .replace("<<score>>", str(item["score"]))

        elif task_type == "case_analysis_merge":
            sys_content = sys_template
            user_content = user_template \
                .replace("<<conversation>>", convo_str) \
                .replace("<<rubric_item>>", rubrics_str)
        
        return [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ]

    def _calculate_metrics(self, task_type: str, grading_json: dict) -> dict:
        """Parses the LLM JSON output into standardized metrics."""
        
        if not grading_json:
             return {"acc": 0.0, "failed": 1}

        try:
            if task_type in ["legal_qa", "document_generation"]:
                # Simple total/max score structure
                score = float(grading_json.get("total_points", 0))
                score_max = float(grading_json.get("max_points", 1)) # Avoid div by zero
                acc = score / score_max if score_max > 0 else 0
                return {
                    "acc": acc,
                    "failed": 0
                }

            elif task_type == "case_analysis_merge":
                # Complex nested structure
                score_details = grading_json["score_details"]
                
                # Mapping Chinese keys to English output keys
                dimensions_map = {
                    "法条依据": "law_acc",
                    "案件事实": "fact_acc",
                    "推理过程": "reasoning_acc",
                    "结论": "conclusion_acc"
                }

                metrics = {}
                total_awarded = 0
                total_max = 0

                for json_key, metric_key in dimensions_map.items():
                    dim_data = score_details[json_key]
                    d_total = float(dim_data["total_points"])
                    d_max = float(dim_data["max_points"])
                    
                    # Calculate sub-metric accuracy
                    rate = d_total / d_max if d_max > 0 else 0.0
                    metrics[metric_key] = rate
                    
                    total_awarded += d_total
                    total_max += d_max

                # Calculate overall accuracy
                overall_acc = total_awarded / total_max if total_max > 0 else 0.0
                
                metrics["acc"] = overall_acc
                metrics["failed"] = 0
                return metrics

        except Exception as e:
            print(f"Error calculating metrics for {task_type}: {e}")
            return {"acc": 0.0, "failed": 1}

