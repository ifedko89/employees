import client from './client'

export function listEmployees(params = {}) {
  return client.get('/employees', { params })
}

export function getEmployee(id) {
  return client.get(`/employees/${id}`)
}

export function createEmployee(data) {
  return client.post('/employees', data)
}

export function updateEmployee(id, data) {
  return client.put(`/employees/${id}`, data)
}

export function deleteEmployee(id) {
  return client.delete(`/employees/${id}`)
}

export function getHistory(id) {
  return client.get(`/employees/${id}/history`)
}
