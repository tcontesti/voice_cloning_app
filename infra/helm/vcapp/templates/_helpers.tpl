{{- define "vcapp.name" -}}{{ .Chart.Name }}{{- end -}}

{{- define "vcapp.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vcapp.labels" -}}
app.kubernetes.io/name: {{ include "vcapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "vcapp.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vcapp.name" . }}
app.kubernetes.io/component: backend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "vcapp.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vcapp.name" . }}
app.kubernetes.io/component: frontend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
