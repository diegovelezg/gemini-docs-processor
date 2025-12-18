Entendido. Aquí tienes el documento completo, estructurado y redactado formalmente como un **Protocolo de Investigación**. Está listo para que lo copies y pegues en el editor (Canvas) y podamos trabajarlo juntos, editando secciones específicas si es necesario.

Este texto integra toda la justificación teórica, la defensa metodológica (vital para la muestra de 8 escuelas) y los scripts técnicos (prompts) en un solo "Manual de Operaciones".

---

# PROTOCOLO DE INVESTIGACIÓN: Evaluación Sistémica Rápida (RSA)

**Proyecto:** Implementación del Modelo JEC y Competencia 28 (TIC) en la Educación Pública.
**Enfoque:** Antropología Digital & Ciencia de la Implementación.

---

## 1. FUNDAMENTACIÓN METODOLÓGICA

### 1.1. Justificación del Enfoque (El "Por qué")

Este estudio adopta un enfoque de **Evaluación Sistémica Rápida (Rapid Systemic Assessment - RSA)**. Frente a la complejidad de la implementación de políticas públicas como la Jornada Escolar Completa (JEC), los métodos cuantitativos tradicionales (encuestas masivas) a menudo capturan la "Teoría Profesada" (lo que se debería hacer) pero fallan en capturar la "Teoría en Uso" (lo que realmente sucede).

Para este diagnóstico, no buscamos **representatividad estadística** (generalizar resultados a todas las escuelas), sino la **saturación de patrones** (identificar mecanismos de fallo recurrentes).

**Premisa Central:** En sistemas complejos, si un mecanismo de bloqueo (ej. "el candado en la sala de innovación") se repite idénticamente en una muestra estratégica de 8 escuelas desconectadas entre sí, estamos ante un **fallo sistémico estructural**, no ante una anécdota aislada.

### 1.2. Marcos Teóricos de Análisis (Los Lentes)

Utilizamos cuatro lentes teóricos para procesar la evidencia:

1. **La Brecha de Implementación (Argyris & Schön):**
* *Objetivo:* Detectar la disonancia entre el discurso normativo ("fomentamos la autonomía") y la práctica factual ("instrucción paso a paso").
* *Utilidad:* Identifica la hipocresía organizacional que impide el cambio.


2. **Teoría de la Complejidad (Dave Snowden - Marco Cynefin):**
* *Objetivo:* Clasificar la naturaleza de los problemas.
* *Calibración:* Distinguimos entre problemas **Complicados** (infraestructura/recursos que requieren gestión) y problemas **Complejos** (cultura/miedos que requieren adaptación).


3. **Innovación en la Sombra (Shadow IT):**
* *Objetivo:* Identificar los "Hacks" o atajos.
* *Utilidad:* Revela la infraestructura real (ej. WhatsApp personal, datos móviles) que subsidia y mantiene operativo el sistema oficial cuando este falla.


4. **Gestión de Polaridades (Barry Johnson):**
* *Objetivo:* Mapear tensiones no resueltas (ej. Control vs. Caos Creativo) que generan los "nudos" operativos.



---

## 2. PROCESO DE ANÁLISIS (Workflow)

El análisis no es lineal. Se estructura en tres fases de destilado de información para garantizar la "Densidad Descriptiva" (Thick Description).

### FASE 1: Minería de Datos (Nivel Micro - Individual)

* **Input:** Transcripción cruda de entrevista (Docente, Director o Estudiante).
* **Acción:** Ejecución secuencial de la **Batería de 5 Prompts** (ver sección 3).
* **Output:** "Ficha de Hallazgos" individual con citas textuales y evidencia factual.

### FASE 2: Síntesis de Roles (Nivel Meso - Agrupación)

* **Input:** Todas las Fichas de Hallazgos agrupadas por tipo de actor.
* **Acción:** Detección de patrones transversales por rol.
* *Ejemplo:* "¿Qué patrón de dolor repiten todos los Directores?" / "¿Qué hack repiten todos los Estudiantes?".


* **Output:** Narrativa Arquetípica (La Voz del Director, La Voz del Estudiante, etc.).

### FASE 3: Triangulación Sistémica (Nivel Macro - El Nudo)

* **Input:** Narrativas Arquetípicas de los 3 roles.
* **Acción:** Ejecución del **Prompt de Triangulación**.
* **Objetivo:** Cruzar perspectivas para encontrar dónde chocan las narrativas y definir el Nudo Crítico.

---

## 3. CAJA DE HERRAMIENTAS: PROMPTS DOCUMENTADOS

Estos son los instrumentos validados para la **FASE 1 (Minería)**.

> **INSTRUCCIÓN MAESTRA (Aplicar a todos):** "Tu prioridad es la Densidad Descriptiva. No resumas ni generalices. Si el actor describe una escena específica o usa una jerga local, mantenla. Prefiero la cita cruda a la categoría abstracta."

### PROMPT 1: DETECTOR DE DISONANCIAS (Lente: Argyris)

**Objetivo:** Desmontar el discurso oficial.

```markdown
# ROL: Auditor Educativo.
# TAREA: Detecta brechas entre "Lo Declarativo" (verbos de deseo/norma) y "Lo Factual" (verbos de acción pasada/eventos).
# FORMATO SALIDA:
1. DECLARATIVO: Citas de intenciones.
2. FACTUAL: Citas de eventos con fecha/lugar.
3. CONTRADICCIÓN: "Dicen X pero la evidencia muestra Y".
   > Mecanismo de Justificación: ¿Qué excusa dan? (Ej: Falta de tiempo, culpa del alumno).

```

### PROMPT 2: MAPEO DE COMPLEJIDAD (Lente: Cynefin)

**Objetivo:** Clasificar para intervenir.

```markdown
# ROL: Experto en Complejidad (Snowden).
# TAREA: Clasifica los problemas según su naturaleza.
# CALIBRACIÓN SECTOR PÚBLICO:
  - SIMPLE: Arreglable por el usuario en 5 min.
  - COMPLICADO: Requiere gestión, presupuesto o expertos (Internet, Luz, Hardware).
  - COMPLEJO: Problemas humanos/culturales (Miedos, Resistencia, Creencias).
# FORMATO SALIDA:
* Dominio [Nombre]: [Problema] -> [Cita] -> [Justificación].

```

### PROMPT 3: TERMÓMETRO EMOCIONAL (Lente: Psicología)

**Objetivo:** Medir la "Indefensión Aprendida".

```markdown
# ROL: Psicólogo Organizacional.
# TAREA: Analiza el subtexto emocional y nivel de Burnout.
# FORMATO SALIDA:
* Estado Dominante: [Ej: Resignación].
* Detonante Específico: ¿Qué objeto/situación dispara la frustración? (Ej: La impresora, la directiva UGEL).
* Evidencia: [Cita textual].

```

### PROMPT 4: HACKS & SHADOW IT (Lente: Etnografía)

**Objetivo:** Descubrir la innovación real.

```markdown
# ROL: Investigador de Shadow IT.
# TAREA: Detecta "Workarounds" (Soluciones informales ante fallos).
# FORMATO SALIDA:
* CASO [N]:
  - Bloqueo (Fallo oficial): [Cita]
  - Atajo (Solución real): [Cita] (Ej: Datos propios, WhatsApp).
  - Riesgo: ¿Excluye a los pobres? ¿Vulnera privacidad?

```

### PROMPT 5: SEÑALES DÉBILES (Lente: Estrategia)

**Objetivo:** Leer lo que no se dice.

```markdown
# ROL: Analista de Inteligencia.
# TAREA: Busca silencios estructurales y eufemismos.
# CONTEXTO: Comparar contra pilares JEC (Inglés, TIC, Pedagogía).
# FORMATO SALIDA:
1. SILENCIOS: Temas ausentes.
2. EUFEMISMOS: Términos que disfrazan la realidad.

```

---

## 4. CONSTRUCCIÓN DE LA MATRIZ DE TENSIONES

Para el reporte final, los hallazgos de la Fase 3 se vuelcan en la siguiente matriz lógica, que permite priorizar intervenciones.

| CLASIFICACIÓN DEL NUDO | DEFINICIÓN (Cruce de Variables) | ESTRATEGIA DE INTERVENCIÓN SUGERIDA |
| --- | --- | --- |
| **I. EL POZO DE RECURSOS** | **Naturaleza:** Complicado (Técnico/Logístico). <br>

<br> **Brecha:** Alta (Dicen que hay, no hay). <br>

<br> *Ej: Internet inoperativo, falta de mantenimiento.* | **Optimización y Gestión.** <br>

<br> No requiere capacitación, requiere arreglar el contrato o el proceso administrativo. |
| **II. EL AGUJERO NEGRO** | **Naturaleza:** Complejo (Cultural). <br>

<br> **Brecha:** Alta (Hipocresía Sistémica). <br>

<br> *Ej: "Taylorismo Digital" (Control disfrazado de autonomía).* | **Cambio de Rituales.** <br>

<br> Requiere modificar incentivos y creencias. La capacitación técnica aquí es inútil. |
| **III. LA ZONA GRIS** | **Naturaleza:** Complejo/Caótico. <br>

<br> **Brecha:** Media (Fricción). <br>

<br> *Ej: Ética Digital (Plagio y Bullying).* | **Normas y Contención.** <br>

<br> Requiere presencia adulta y nuevos acuerdos de convivencia. |

---

**Nota Final:** Este protocolo garantiza la trazabilidad del dato. Cada afirmación en el informe final ("El sistema padece de Taylorismo Digital") puede rastrearse hasta una cita textual específica extraída en la Fase 1 y triangulada en la Fase 3, blindando la investigación ante críticas metodológicas.