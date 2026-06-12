import streamlit as st
from datetime import datetime
import re

st.set_page_config(page_title="MediTriage AI", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .emergency {
        background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .doctor {
        background: linear-gradient(135deg, #feca57, #ff9f43);
        padding: 20px;
        border-radius: 10px;
        color: #333;
    }
    .home {
        background: linear-gradient(135deg, #48dbfb, #0abde3);
        padding: 20px;
        border-radius: 10px;
        color: #333;
    }
    .recommendation-box {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🏥 MediTriage AI</h1><p>Professional Medical Symptom Assessment</p></div>', unsafe_allow_html=True)

# ============================================
# MEMORY / STATE MANAGEMENT
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "step" not in st.session_state:
    st.session_state.step = 0

if "patient_symptom" not in st.session_state:
    st.session_state.patient_symptom = ""
if "patient_duration" not in st.session_state:
    st.session_state.patient_duration = ""
if "patient_severity" not in st.session_state:
    st.session_state.patient_severity = ""
if "patient_other" not in st.session_state:
    st.session_state.patient_other = ""

# Store ALL previous conversations for memory recall
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ============================================
# PROFESSIONAL MEDICAL TOOL
# ============================================

def get_medical_advice(symptom, duration, severity, other):
    """TOOL: Returns DIFFERENT medical recommendations based on symptoms"""
    symptom_lower = symptom.lower()
    other_lower = other.lower()
    combined = symptom_lower + " " + other_lower
    
    # Extract severity as number
    severity_num = 5
    try:
        severity_num = int(float(severity)) if str(severity).replace('.', '').replace('-', '').isdigit() else 5
    except:
        severity_num = 5
    
    # ============================================
    # LEVEL 1: EMERGENCY - CRITICAL SYMPTOMS
    # ============================================
    emergency = ["chest pain", "difficulty breathing", "can't breathe", "heart attack", 
                 "severe bleeding", "unconscious", "stroke", "paralysis", "cannot speak"]
    for word in emergency:
        if word in combined:
            return {
                "level": "EMERGENCY - CALL 911",
                "color": "emergency",
                "advice": f"""
### 🚨 MEDICAL EMERGENCY - CALL 911 IMMEDIATELY 🚨

**Your symptoms:** {symptom}
**Severity:** {severity_num}/10

**THIS IS A MEDICAL EMERGENCY. DO NOT WAIT.**

#### What to do RIGHT NOW:
1. **Call 911 (or emergency services) immediately**
2. **Go to the nearest Emergency Room**
3. **Do NOT drive yourself - get someone to take you**

**Time matters. Seek help now.**
"""
            }
    
    # ============================================
    # LEVEL 2: HEADACHE WITH FEVER - MUST SEE DOCTOR
    # ============================================
    if ("headache" in symptom_lower or "migraine" in symptom_lower) and ("fever" in other_lower or "temperature" in other_lower):
        return {
            "level": "SEE A DOCTOR - Headache with Fever",
            "color": "doctor",
            "advice": f"""
### 👨‍⚕️ DOCTOR VISIT RECOMMENDED

**Your symptoms:** {symptom} with fever
**Duration:** {duration}
**Severity:** {severity_num}/10

#### Why you should see a doctor:
Headache accompanied by fever can indicate an infection (sinusitis, flu, or more serious conditions). Medical evaluation is recommended.

#### Recommended actions within 24 hours:
1. **Schedule an appointment with your doctor today**
2. **Monitor your temperature - write down fever readings**
3. **Rest and stay hydrated**
4. **Take acetaminophen (Tylenol) for fever/pain**

#### When to go to ER immediately:
- Severe headache with stiff neck
- Fever above 103°F (39.4°C)
- Confusion or difficulty speaking
- Sensitivity to light

**Do not ignore headache with fever - get evaluated.**
"""
        }
    
    # ============================================
    # LEVEL 3: FEVER WITH OTHER SYMPTOMS
    # ============================================
    if "fever" in other_lower or "fever" in symptom_lower:
        if severity_num >= 5:
            return {
                "level": "SEE A DOCTOR - Fever",
                "color": "doctor",
                "advice": f"""
### 👨‍⚕️ DOCTOR VISIT RECOMMENDED

**Your symptoms:** {symptom} with fever
**Duration:** {duration}
**Severity:** {severity_num}/10

#### Why you should see a doctor:
Fever with moderate to severe symptoms requires medical evaluation to rule out infection.

#### Recommended actions:
1. **See a doctor within 24-48 hours**
2. **Monitor temperature every 4 hours**
3. **Rest and stay hydrated**
4. **Take fever-reducing medication (acetaminophen/ibuprofen)**

#### Go to ER if:
- Fever above 103°F (39.4°C)
- Difficulty breathing
- Severe headache with stiff neck
- Confusion or seizures
"""
            }
        else:
            return {
                "level": "MONITOR FEVER - See if worsens",
                "color": "doctor",
                "advice": f"""
### 🌡️ MONITOR YOUR FEVER

**Your symptoms:** {symptom} with mild fever
**Duration:** {duration}
**Severity:** {severity_num}/10

#### Home care with fever monitoring:
1. **Check temperature every 4-6 hours**
2. **Rest and stay hydrated**
3. **Take fever reducers if uncomfortable**
4. **See a doctor if fever lasts >3 days**

#### When to see a doctor:
- Fever goes above 101°F (38.3°C)
- Fever lasts more than 3 days
- New symptoms develop
- You feel worse after 48 hours
"""
            }
    
    # ============================================
    # LEVEL 4: NAUSEA - SPECIFIC ADVICE
    # ============================================
    if "nausea" in symptom_lower or "nausea" in other_lower:
        if severity_num >= 6:
            return {
                "level": "SEE A DOCTOR - Severe Nausea",
                "color": "doctor",
                "advice": f"""
### 👨‍⚕️ DOCTOR VISIT RECOMMENDED

**Your symptoms:** Nausea (Severity: {severity_num}/10)
**Duration:** {duration}

#### Why you should see a doctor:
Severe nausea may indicate gastroenteritis, food poisoning, or other conditions needing medical attention.

#### Immediate steps:
1. **Sip clear liquids slowly (water, ginger ale, electrolyte drinks)**
2. **Avoid solid food for a few hours**
3. **Try ginger tea or peppermint tea**
4. **See a doctor if vomiting persists**

#### Go to ER if:
- Unable to keep any liquids down for 12 hours
- Blood in vomit
- Severe abdominal pain
- Signs of dehydration (dry mouth, no urination for 8 hours)
"""
            }
        else:
            return {
                "level": "HOME CARE - Mild Nausea",
                "color": "home",
                "advice": f"""
### 🏠 HOME CARE FOR NAUSEA

**Your symptoms:** Nausea (Severity: {severity_num}/10)
**Duration:** {duration}

#### Home care instructions for nausea:

**What to do:**
1. **Sip clear liquids slowly** - water, ginger ale, electrolyte drinks
2. **Try the BRAT diet** - Bananas, Rice, Applesauce, Toast (when ready to eat)
3. **Ginger tea or peppermint tea** - natural anti-nausea remedies
4. **Rest in a comfortable position** - propped up with pillows
5. **Avoid strong smells** - perfumes, cooking odors

**What to avoid:**
- Fatty, fried, or spicy foods
- Dairy products
- Caffeine and alcohol
- Large meals

**When to see a doctor:**
- Nausea lasts more than 48 hours
- Unable to keep liquids down
- Signs of dehydration
- Severe abdominal pain
- Blood in vomit

**Expected recovery:** Most mild nausea resolves within 24-48 hours with home care.
"""
            }
    
    # ============================================
    # LEVEL 5: HEADACHE (without fever) - SPECIFIC
    # ============================================
    if "headache" in symptom_lower:
        if severity_num >= 7:
            return {
                "level": "SEE A DOCTOR - Severe Headache",
                "color": "doctor",
                "advice": f"""
### 👨‍⚕️ DOCTOR VISIT RECOMMENDED

**Your symptoms:** Severe headache
**Duration:** {duration}
**Severity:** {severity_num}/10

#### Why you should see a doctor:
Severe headaches (7+/10) may indicate migraine or other conditions needing medical attention.

#### Immediate steps:
1. **Rest in a dark, quiet room**
2. **Apply cold compress to forehead**
3. **Take OTC pain relievers (ibuprofen/acetaminophen)**
4. **Stay hydrated**

#### Go to ER immediately if:
- Worst headache of your life
- Headache with stiff neck and fever
- Headache after head injury
- Sudden onset severe headache
"""
            }
        else:
            return {
                "level": "HOME CARE - Mild Headache",
                "color": "home",
                "advice": f"""
### 🏠 HOME CARE FOR HEADACHE

**Your symptoms:** Headache (Severity: {severity_num}/10)
**Duration:** {duration}

#### Home care instructions:

**Immediate relief:**
1. **Rest in a dark, quiet room**
2. **Apply cold or warm compress to forehead/neck**
3. **Drink water** - dehydration is a common cause
4. **Take OTC pain relievers** (ibuprofen, acetaminophen)

**Prevention:**
- Maintain regular sleep schedule
- Stay hydrated throughout the day
- Avoid skipping meals
- Manage stress with deep breathing

**When to see a doctor:**
- Headache lasts more than 3 days
- Pain becomes severe (7+/10)
- Headache with fever, stiff neck, or vision changes
- Headaches become more frequent

**Most tension headaches resolve within 24 hours with rest and hydration.**
"""
            }
    
    # ============================================
    # DEFAULT: GENERAL HOME CARE
    # ============================================
    return {
        "level": "HOME CARE",
        "color": "home",
        "advice": f"""
### 🏠 HOME CARE RECOMMENDED

**Your symptoms:** {symptom}
**Duration:** {duration}
**Severity:** {severity_num}/10
**Other symptoms:** {other}

#### General Home Care Instructions:

**1. REST**
- Get 8-10 hours of sleep
- Take breaks during the day
- Avoid strenuous activities

**2. HYDRATION**
- Drink 8-10 glasses of water daily
- Try warm liquids (tea, soup)
- Avoid caffeine and alcohol

**3. NUTRITION**
- Eat small, frequent meals
- Choose light, easily digestible foods
- Avoid spicy, fried, or heavy foods

**4. MONITORING**
- Track your symptoms daily
- Note any changes or new symptoms
- Check temperature if you feel feverish

#### When to See a Doctor:
- Symptoms last more than 3-5 days
- Severity increases to 7/10 or higher
- New symptoms develop
- Fever above 101°F (38.3°C)

#### Expected Recovery:
- Days 1-2: Rest and monitor
- Days 3-4: Gradual improvement
- Day 5-7: Most mild symptoms resolve

---
*Keep this information for reference. You can ask me "What did I tell you before?" to recall this assessment.*
"""
    }

# ============================================
# MEMORY RECALL FUNCTION
# ============================================

def recall_previous_conversation():
    """Returns what the user said in their last conversation"""
    if st.session_state.conversation_history:
        last = st.session_state.conversation_history[-1]
        return f"""
### 🧠 I Remember Our Last Conversation:

**You told me:**
- **Symptom:** {last['symptom']}
- **Duration:** {last['duration']}
- **Severity:** {last['severity']}/10
- **Other symptoms:** {last['other']}

**My recommendation was:** {last['triage']}

**That conversation happened at:** {last['timestamp']}

---
Would you like to:
- Start a new assessment for a different symptom?
- Get more details about the previous recommendation?
"""
    else:
        return "We haven't completed any assessments yet. Please describe your symptoms to start."

# ============================================
# CHECK INPUT TYPE
# ============================================

def is_memory_question(user_input):
    memory_keywords = ["what did i", "what was my", "remember", "recall", "previous", "before", "earlier", "last time", "what did you", "what did we", "conversation", "tell you before", "asked before"]
    return any(keyword in user_input.lower() for keyword in memory_keywords)

# ============================================
# DISPLAY CHAT
# ============================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================
# INITIAL GREETING
# ============================================

if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        greeting = """Hello! I'm MediTriage AI, your professional medical assessment assistant.

**How I work:**
1. You describe your symptoms
2. I ask 3 quick questions (duration, severity, other symptoms)
3. I provide a detailed, personalized medical recommendation

**To begin, please describe your main symptom:** (e.g., "I have a headache", "Chest pain", "Fever and cough")"""
        st.markdown(greeting)
        st.session_state.messages.append({"role": "assistant", "content": greeting})

# ============================================
# USER INPUT HANDLING
# ============================================

user_input = st.chat_input("Type your response here...")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Check if memory question
    if is_memory_question(user_input):
        memory_response = recall_previous_conversation()
        with st.chat_message("assistant"):
            st.markdown(memory_response)
            st.session_state.messages.append({"role": "assistant", "content": memory_response})
    
    # Normal assessment flow
    else:
        current_step = st.session_state.step
        
        if current_step == 0:
            st.session_state.patient_symptom = user_input
            response = "📋 **Question 1 of 3:** How long have you been experiencing these symptoms? (e.g., '2 days', '1 week', 'just started')"
            st.session_state.step = 1
            with st.chat_message("assistant"):
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif current_step == 1:
            st.session_state.patient_duration = user_input
            response = "📊 **Question 2 of 3:** On a scale of 1 to 10, how severe is your discomfort? (1 = very mild, 10 = very severe)"
            st.session_state.step = 2
            with st.chat_message("assistant"):
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif current_step == 2:
            # Extract number from severity
            severity_value = user_input
            numbers = re.findall(r'\d+', user_input)
            if numbers:
                severity_value = numbers[0]
            st.session_state.patient_severity = severity_value
            response = "🔍 **Question 3 of 3:** Are you experiencing any other symptoms? (e.g., fever, nausea, dizziness, or 'none')"
            st.session_state.step = 3
            with st.chat_message("assistant"):
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif current_step == 3:
            st.session_state.patient_other = user_input
            
            # Get detailed advice
            advice = get_medical_advice(
                st.session_state.patient_symptom,
                st.session_state.patient_duration,
                st.session_state.patient_severity,
                st.session_state.patient_other
            )
            
            # Store in memory
            st.session_state.conversation_history.append({
                "symptom": st.session_state.patient_symptom,
                "duration": st.session_state.patient_duration,
                "severity": st.session_state.patient_severity,
                "other": st.session_state.patient_other,
                "triage": advice['level'],
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            
            # Build final response with summary
            final_response = f"""
### 📋 Complete Assessment Report

| Category | Your Information |
|----------|------------------|
| **Primary Symptom** | {st.session_state.patient_symptom} |
| **Duration** | {st.session_state.patient_duration} |
| **Severity Level** | {st.session_state.patient_severity}/10 |
| **Additional Symptoms** | {st.session_state.patient_other} |
| **Assessment Time** | {datetime.now().strftime("%I:%M %p")} |

---

{advice['advice']}

---

### 📝 Summary Checklist

- [x] Symptoms assessed: {st.session_state.patient_symptom}
- [x] Duration recorded: {st.session_state.patient_duration}
- [x] Severity noted: {st.session_state.patient_severity}/10
- [x] Recommendations provided based on your specific case

---
**Next Steps:**
1. Follow the recommendations above
2. Monitor your symptoms closely
3. **You can ask me: "What did I tell you before?"** to recall this assessment
4. Describe new symptoms for another assessment
"""
            
            # Display with styling
            if advice['color'] == 'emergency':
                st.markdown('<div class="emergency">', unsafe_allow_html=True)
            elif advice['color'] == 'doctor':
                st.markdown('<div class="doctor">', unsafe_allow_html=True)
            else:
                st.markdown('<div class="home">', unsafe_allow_html=True)
            
            with st.chat_message("assistant"):
                st.markdown(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Reset for next conversation
            st.session_state.step = 0
            st.session_state.patient_symptom = ""
            st.session_state.patient_duration = ""
            st.session_state.patient_severity = ""
            st.session_state.patient_other = ""

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("## 🏥 MediTriage AI")
    st.markdown("*Professional Medical Assessment*")
    
    st.markdown("---")
    
    st.markdown("### 🧠 Memory Status")
    st.markdown(f"**Session ID:** `{st.session_state.thread_id[:16]}...`")
    st.markdown(f"**Assessments Completed:** {len(st.session_state.conversation_history)}")
    
    if st.session_state.conversation_history:
        st.markdown("**Previous Assessments:**")
        for i, conv in enumerate(st.session_state.conversation_history[-3:], 1):
            st.markdown(f"{i}. {conv['symptom'][:30]} → **{conv['triage']}**")
    
    st.markdown("---")
    st.markdown("### 💡 Test Memory Feature")
    st.markdown("After completing an assessment, type:")
    st.code("What did I tell you before?")
    
    st.markdown("---")
    st.markdown("### 📋 Assessment Process")
    st.markdown("""
    1. **Describe** your main symptom
    2. **Answer** 3 questions (duration, severity, other)
    3. **Receive** detailed personalized recommendations
    4. **Ask** "What did I tell you before?" to test memory
    """)
    
    st.markdown("---")
    
    if st.button("🔄 Start Fresh", use_container_width=True):
        st.session_state.messages = []
        st.session_state.step = 0
        st.session_state.patient_symptom = ""
        st.session_state.patient_duration = ""
        st.session_state.patient_severity = ""
        st.session_state.patient_other = ""
        st.session_state.conversation_history = []
        st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.rerun()
    
    st.caption("⚠️ For educational purposes. Consult a doctor for medical advice.")