using UnityEngine;

public class AAAConfigurator : MonoBehaviour
{
    [Header("Engine Overrides")]
    [Tooltip("Forces the Android device to render at maximum target framerate.")]
    public bool force60FPS = true;
    
    [Tooltip("Forces high-quality texture rendering at oblique camera angles.")]
    public bool forceAnisotropic = true;

    void Awake()
    {
        // Execute the "Solid" framerate lock
        if (force60FPS)
        {
            Application.targetFrameRate = 60;
            Debug.Log("[SRA-01] V-Sync overridden. Target Frame Rate locked to 60.");
        }

        // Execute the "Solid" texture filtering
        if (forceAnisotropic)
        {
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
            Debug.Log("[SRA-01] Anisotropic Filtering Forced ON for AAA visual fidelity.");
        }

        // Prevent the Android screen from dimming or sleeping during gameplay
        Screen.sleepTimeout = SleepTimeout.NeverSleep;
    }
}