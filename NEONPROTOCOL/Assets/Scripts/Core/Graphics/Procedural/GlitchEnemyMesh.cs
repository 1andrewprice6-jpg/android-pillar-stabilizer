using UnityEngine;

namespace NeonProtocol.Core.Graphics.Procedural
{
    public class GlitchEnemyMesh : MonoBehaviour
    {
        // Generates a jagged, glitchy mesh for the zombie
        // Instead of a T-Pose human, we generate a "Corrupted Data Chunk"

        private void Start()
        {
            Mesh mesh = new Mesh();
            
            // Simple procedural shape logic (e.g., a jagged crystal)
            Vector3[] vertices = new Vector3[]
            {
                new Vector3(0, 0, 0),
                new Vector3(1, 0, 0),
                new Vector3(0, 2, 0),
                new Vector3(0, 0, 1),
                new Vector3(0.5f, 2.5f, 0.5f) // The "Head"
            };
            
            int[] triangles = new int[]
            {
                0, 2, 1,
                0, 3, 2,
                1, 2, 3,
                2, 3, 4,
                2, 4, 1,
                1, 4, 3
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            
            GetComponent<MeshFilter>().mesh = mesh;
            
            // Apply Hologram Shader
            if (NeonShaderFactory.Instance)
                GetComponent<Renderer>().material = NeonShaderFactory.Instance.neonZombieMat;
        }
    }
}