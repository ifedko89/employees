import client from './client'

export function listPositions() {
  return client.get('/positions')
}

export function createPosition(name) {
  return client.post('/positions', { name })
}

export function updatePosition(id, name) {
  return client.put(`/positions/${id}`, { name })
}

export function deletePosition(id) {
  return client.delete(`/positions/${id}`)
}
