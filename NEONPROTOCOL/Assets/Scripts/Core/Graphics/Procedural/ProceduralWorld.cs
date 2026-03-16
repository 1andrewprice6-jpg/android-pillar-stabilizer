using UnityEngine;

namespace NeonProtocol.Core.Graphics.Procedural
{
    public class ProceduralWorld : MonoBehaviour
    {
        public int mapSize = 50;
        public int obstacleCount = 20;

        private void Start()
        {
            GenerateFloor();
            GenerateObstacles();
        }

        private void GenerateFloor()
        {
            GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.transform.localScale = new Vector3(mapSize, 1, mapSize);
            floor.name = "Simulation_Floor";
            
            // Assign Neon Material
            var rend = floor.GetComponent<Renderer>();
            if (NeonShaderFactory.Instance)
                rend.material = NeonShaderFactory.Instance.neonGridMat;
        }

        private void GenerateObstacles()
        {
            for (int i = 0; i < obstacleCount; i++)
            {
                // Create random geometric shapes
                GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                obj.name = $"Construct_{i}";
                
                // Random position
                float x = Random.Range(-mapSize * 4, mapSize * 4);
                float z = Random.Range(-mapSize * 4, mapSize * 4);
                
                // Random Scale
                float h = Random.Range(2f, 10f);
                float w = Random.Range(1f, 5f);
                
                obj.transform.position = new Vector3(x, h/2, z);
                obj.transform.localScale = new Vector3(w, h, w);

                // Assign Material
                var rend = obj.GetComponent<Renderer>();
                if (NeonShaderFactory.Instance)
                    rend.material = NeonShaderFactory.Instance.neonWallMat;
                
                // Add collision for gameplay
                obj.AddComponent<BoxCollider>();
                
                // Make it static for baking
                obj.isStatic = true;
            }
        }
    }
}